import os
import uuid

import httpx
from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIServerError,
    ApplicationNotFoundError,
    AudioFileTooLargeError,
    InvalidAudioFileError,
    QuestionNotFoundError,
    SpeechPracticeAlreadyExistsError,
    ResumeTooShortError,
    SpeechPracticeNotAllowedError,
)
from app.models.application import (
    Application,
    ApplicationStatusEnum,
    PersonalStatement,
    Question,
    StageEnum,
)
from app.models.submission import (
    InputTypeEnum,
    SpeechAcoustic,
    SpeechAnalysis,
    SpeechContent,
    Submission,
)
from app.schemas.speech import SpeechPracticeCreateReq

# 스피치 연습이 활성화되는 (전형 단계, 진행 상태) 조합
ALLOWED_STAGES: set[tuple[StageEnum, ApplicationStatusEnum]] = {
    (StageEnum.DOCUMENT, ApplicationStatusEnum.COMPLETED),
    (StageEnum.CODING_TEST, ApplicationStatusEnum.PREPARING),
    (StageEnum.CODING_TEST, ApplicationStatusEnum.COMPLETED),
    (StageEnum.FIRST_INTERVIEW, ApplicationStatusEnum.PREPARING),
    (StageEnum.FIRST_INTERVIEW, ApplicationStatusEnum.COMPLETED),
    (StageEnum.SECOND_INTERVIEW, ApplicationStatusEnum.PREPARING),
    (StageEnum.FINAL_INTERVIEW, ApplicationStatusEnum.PREPARING),
}

_AI_TIMEOUT_SECONDS = 90.0
# 스피치 분석은 오디오 전사 + 분석이라 질문 생성보다 더 오래 걸릴 수 있어 넉넉히 잡는다.
_SPEECH_AI_TIMEOUT_SECONDS = 180.0
# AI /question-extract 는 자소서가 이보다 짧으면 400 을 반환 (AI API v2)
# 왕복을 돌기 전에 백엔드에서 먼저 걸러 명확한 에러를 반환함.
_MIN_RESUME_LENGTH = 50
_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav"}
_MAX_AUDIO_BYTES = 100 * 1024 * 1024  # 100MB


def _extract_questions(company: str, role: str, resume_text: str) -> list[dict]:
    """AI 서버의 POST /question-extract를 호출해 예상 질문 목록을 받아온다."""
    try:
        with httpx.Client(timeout=_AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_SERVER_URL}/question-extract",
                json={"company": company, "role": role, "resume_text": resume_text},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        raise AIServerError()

    return data.get("questions", [])


async def _extract_questions_async(
    company: str, role: str, resume_text: str
) -> list[dict]:
    """_extract_questions 의 비동기 버전.

    동기 httpx.Client 는 AI 응답(수십 초) 동안 워커 스레드를 통째로 붙잡지만,
    AsyncClient + await 는 그 시간을 이벤트 루프에서 다중화한다. 단일 워커가
    수많은 in-flight AI 호출을 동시에 흘려보낼 수 있다.
    """
    try:
        async with httpx.AsyncClient(timeout=_AI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.AI_SERVER_URL}/question-extract",
                json={"company": company, "role": role, "resume_text": resume_text},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        raise AIServerError()

    return data.get("questions", [])


def _build_resume_text(statements) -> str:
    """자소서 문항/내용을 AI 에 보낼 하나의 텍스트로 합치고 최소 길이를 검증함."""
    resume_text = "\n\n".join(f"{item.question}\n{item.content}" for item in statements)
    if len(resume_text.strip()) < _MIN_RESUME_LENGTH:
        raise ResumeTooShortError()
    return resume_text


def _get_owned_application(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
    # 본인 소유의 지원 현황을 조회
    application = (
        db.query(Application)
        .filter(
            Application.application_id == application_id,
            Application.user_id == user_id,
        )
        .first()
    )
    if not application:
        raise ApplicationNotFoundError()
    return application


def create_speech_practice(
    db: Session, user_id: uuid.UUID, body: SpeechPracticeCreateReq
) -> tuple[uuid.UUID, list[Question]]:
    application = _get_owned_application(db, user_id, body.application_id)

    if (application.stage, application.status) not in ALLOWED_STAGES:
        raise SpeechPracticeNotAllowedError()

    already_exists = (
        db.query(Question.question_id)
        .filter(Question.application_id == application.application_id)
        .first()
    )
    if already_exists:
        raise SpeechPracticeAlreadyExistsError()

    for sequence, item in enumerate(body.personal_statements, start=1):
        db.add(
            PersonalStatement(
                application_id=application.application_id,
                question=item.question,
                content=item.content,
                sequence=sequence,
            )
        )

    resume_text = _build_resume_text(body.personal_statements)

    extracted = _extract_questions(body.company_name, body.position, resume_text)

    questions = [
        Question(
            application_id=application.application_id,
            question=item.get("question", ""),
            category=item.get("category"),
            sequence=sequence,
        )
        for sequence, item in enumerate(extracted, start=1)
    ]
    db.add_all(questions)

    db.commit()
    for question in questions:
        db.refresh(question)

    return application.application_id, questions


def list_questions(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> tuple[list[Question], set[uuid.UUID]]:
    """저장된 질문 목록과 연습(제출) 완료된 질문 ID 집합을 반환"""
    application = _get_owned_application(db, user_id, application_id)

    questions = (
        db.query(Question)
        .filter(Question.application_id == application.application_id)
        .order_by(Question.sequence)
        .all()
    )
    if not questions:
        return [], set()

    practiced_ids = {
        question_id
        for (question_id,) in db.query(Submission.question_id)
        .filter(Submission.question_id.in_([q.question_id for q in questions]))
        .distinct()
        .all()
    }
    return questions, practiced_ids


def generate_more_questions(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> list[Question]:
    """AI 재호출 및 예상 질문을 추가 생성
    기존 질문과 텍스트가 완전히 일치하는 항목은 제외"""
    application = _get_owned_application(db, user_id, application_id)

    if (application.stage, application.status) not in ALLOWED_STAGES:
        raise SpeechPracticeNotAllowedError()

    statements = (
        db.query(PersonalStatement)
        .filter(PersonalStatement.application_id == application.application_id)
        .order_by(PersonalStatement.sequence)
        .all()
    )
    resume_text = _build_resume_text(statements)

    extracted = _extract_questions(
        application.company_name, application.position, resume_text
    )

    existing_texts = {
        text
        for (text,) in db.query(Question.question)
        .filter(Question.application_id == application.application_id)
        .all()
    }
    max_sequence = (
        db.query(func.max(Question.sequence))
        .filter(Question.application_id == application.application_id)
        .scalar()
        or 0
    )

    new_questions: list[Question] = []
    seen = set(existing_texts)
    sequence = max_sequence
    for item in extracted:
        text = item.get("question", "")
        if not text or text in seen:
            continue
        seen.add(text)
        sequence += 1
        new_questions.append(
            Question(
                application_id=application.application_id,
                question=text,
                category=item.get("category"),
                sequence=sequence,
            )
        )

    if new_questions:
        db.add_all(new_questions)
        db.commit()
        for question in new_questions:
            db.refresh(question)

    return new_questions


def _read_generate_inputs(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> tuple[uuid.UUID, str, str, str, set[str], int]:
    """generate 의 동기 DB 읽기 단계.

    소유권 검증 + 자소서/기존 질문/max sequence 조회 후 commit 으로 트랜잭션을
    끝내 **커넥션을 풀에 반환**한다. 이후의 AI 호출(수 초)은 커넥션을 붙잡지 않는다.
    → 커넥션 풀(15) 이 AI 대기 시간에 묶이지 않아 동시성 상한이 크게 오른다.
    """
    application = _get_owned_application(db, user_id, application_id)
    if (application.stage, application.status) not in ALLOWED_STAGES:
        raise SpeechPracticeNotAllowedError()

    statements = (
        db.query(PersonalStatement)
        .filter(PersonalStatement.application_id == application.application_id)
        .order_by(PersonalStatement.sequence)
        .all()
    )
    resume_text = _build_resume_text(statements)
    existing_texts = {
        text
        for (text,) in db.query(Question.question)
        .filter(Question.application_id == application.application_id)
        .all()
    }
    max_sequence = (
        db.query(func.max(Question.sequence))
        .filter(Question.application_id == application.application_id)
        .scalar()
        or 0
    )
    # AI 호출에 필요한 값은 primitive 로 뽑아둔다 (commit 후 ORM 객체는 만료됨).
    app_id = application.application_id
    company = application.company_name
    position = application.position
    db.commit()  # 읽기 트랜잭션 종료 → 커넥션 반환 (AI await 동안 미점유)
    return app_id, company, position, resume_text, existing_texts, max_sequence


async def generate_more_questions_async(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> list[Question]:
    """generate_more_questions 의 비동기 버전.

    (동기 읽기 → 커넥션 반환) → (AI await, 커넥션 미점유) → (동기 쓰기) 순서로
    외부 I/O 대기 동안 DB 커넥션·워커 스레드를 모두 놓는다.
    """
    app_id, company, position, resume_text, existing_texts, max_sequence = (
        _read_generate_inputs(db, user_id, application_id)
    )

    extracted = await _extract_questions_async(company, position, resume_text)

    new_questions: list[Question] = []
    seen = set(existing_texts)
    sequence = max_sequence
    for item in extracted:
        text = item.get("question", "")
        if not text or text in seen:
            continue
        seen.add(text)
        sequence += 1
        new_questions.append(
            Question(
                application_id=app_id,
                question=text,
                category=item.get("category"),
                sequence=sequence,
            )
        )

    if new_questions:
        db.add_all(new_questions)
        db.commit()
        for question in new_questions:
            db.refresh(question)

    return new_questions


def _get_owned_question(
    db: Session, user_id: uuid.UUID, question_id: uuid.UUID
) -> Question:
    # 질문 -> 지원현황 -> 사용자로 소유권을 검증 (남의 질문에 제출 불가)
    question = (
        db.query(Question)
        .join(Application, Question.application_id == Application.application_id)
        .filter(
            Question.question_id == question_id,
            Application.user_id == user_id,
        )
        .first()
    )
    if not question:
        raise QuestionNotFoundError()
    return question


def _save_audio_file(upload: UploadFile, file_stem: str) -> str:
    """업로드된 음성 파일을 공유 볼륨에 저장하고 절대 경로를 반환.

    백엔드와 AI 서버가 같은 볼륨을 공유하므로 여기서 만든 절대 경로를
    그대로 AI 서버의 audio_file_path로 넘긴다.
    """
    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in _ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidAudioFileError()

    os.makedirs(settings.AUDIO_UPLOAD_DIR, exist_ok=True)
    dest_path = os.path.join(settings.AUDIO_UPLOAD_DIR, f"{file_stem}{ext}")

    size = 0
    try:
        with open(dest_path, "wb") as out:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > _MAX_AUDIO_BYTES:
                    raise AudioFileTooLargeError()
                out.write(chunk)
    except AudioFileTooLargeError:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise

    return os.path.abspath(dest_path)


def _analyze_speech_ai(audio_file_path: str, question_text: str) -> dict:
    """AI 서버의 POST /speech-analyze를 호출해 스피치 분석 결과를 받아온다."""
    try:
        with httpx.Client(timeout=_SPEECH_AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_SERVER_URL}/speech-analyze",
                json={
                    "audio_path": audio_file_path,
                    "question_text": question_text,
                },
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        raise AIServerError()


def analyze_speech(
    db: Session,
    user_id: uuid.UUID,
    question_id: uuid.UUID,
    upload: UploadFile,
    input_type: InputTypeEnum,
) -> tuple[Submission, dict]:
    """음성 파일을 공유 볼륨에 저장 → AI 스피치 분석 호출 → 제출/분석 결과를 영속화."""
    question = _get_owned_question(db, user_id, question_id)

    audio_path = _save_audio_file(upload, uuid.uuid4().hex)
    try:
        result = _analyze_speech_ai(audio_path, question.question)
    except AIServerError:
        # AI 호출이 실패하면 방금 저장한 음성 파일을 정리한다 (재시도 시 새로 업로드).
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise

    submission = Submission(
        question_id=question.question_id,
        input_type=input_type,
        file_url=audio_path,
    )
    db.add(submission)
    db.flush()

    acoustic = result.get("acoustic") or {}
    content = result.get("content") or {}

    # v2 에는 최상위 feedback 이 없음 (종합 피드백은 content.overall)
    analysis = SpeechAnalysis(submission_id=submission.submission_id)
    db.add(analysis)
    db.flush()

    db.add(
        SpeechAcoustic(
            speech_analysis_id=analysis.speech_analysis_id,
            speed_wpm=acoustic.get("speed_wpm"),
            speed_label=acoustic.get("speed_label"),
            filler_words=acoustic.get("filler_words"),
            silence_count=acoustic.get("silence_count"),
            duration_sec=acoustic.get("duration_sec"),
            word_count=acoustic.get("word_count"),
        )
    )
    db.add(
        SpeechContent(
            speech_analysis_id=analysis.speech_analysis_id,
            question_type=content.get("question_type"),
            # 행동형 질문이 아니면 star_score 는 null 로 온다.
            # `or {}` 를 쓰면 빈 객체가 되어 CHECK 제약에 걸리므로 그대로 넘긴다.
            star_score=content.get("star_score"),
            coherence=content.get("coherence"),
            keyword_repeat=content.get("keyword_repeat"),
            negative_reframe=content.get("negative_reframe"),
            overall=content.get("overall"),
        )
    )

    db.commit()
    db.refresh(submission)

    return submission, result
