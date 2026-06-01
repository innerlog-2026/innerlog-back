import uuid

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIServerError,
    ApplicationNotFoundError,
    SpeechPracticeNotAllowedError,
)
from app.models.application import (
    Application,
    ApplicationStatusEnum,
    PersonalStatement,
    Question,
    StageEnum,
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


def create_speech_practice(
    db: Session, user_id: uuid.UUID, body: SpeechPracticeCreateReq
) -> tuple[uuid.UUID, list[Question]]:
    application = (
        db.query(Application)
        .filter(
            Application.application_id == body.application_id,
            Application.user_id == user_id,
        )
        .first()
    )
    if not application:
        raise ApplicationNotFoundError()

    if (application.stage, application.status) not in ALLOWED_STAGES:
        raise SpeechPracticeNotAllowedError()

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
