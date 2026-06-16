import uuid

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIServerError,
    ApplicationNotFoundError,
    SpeechPracticeAlreadyExistsError,
    SpeechPracticeNotAllowedError,
)
from app.models.application import (
    Application,
    ApplicationStatusEnum,
    PersonalStatement,
    Question,
    StageEnum,
)
from app.models.submission import Submission
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

    resume_text = "\n\n".join(
        f"{item.question}\n{item.content}" for item in body.personal_statements
    )

    extracted = _extract_questions(body.company_name, body.position, resume_text)

    questions = [
        Question(
            application_id=application.application_id,
            question=item.get("text", ""),
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
    resume_text = "\n\n".join(f"{item.question}\n{item.content}" for item in statements)

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
        text = item.get("text", "")
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
