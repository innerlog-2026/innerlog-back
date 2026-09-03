import logging
import uuid
from typing import Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AIServerError,
    ApplicationNotFoundError,
    RetrospectAlreadyDoneError,
    RetrospectAlreadyExistsError,
    RetrospectNotAllowedError,
    RetrospectNotDoneError,
    RetrospectNotInProgressError,
    SessionNotFoundError,
)
from app.models.application import Application, ApplicationStatusEnum, StageEnum
from app.models.session import (
    Chat,
    InterviewAnalysis,
    SenderEnum,
    Session as SessionModel,
    SessionStageEnum,
    SessionStatusEnum,
    SessionTypeEnum,
)
from app.schemas.retrospect import RetrospectCreateRequest

logger = logging.getLogger(__name__)

# 면접 회고가 활성화되는 전형 단계 → 회고 세션 타입 매핑
# status는 COMPLETED여야 함
_STAGE_TO_TYPE: dict[StageEnum, SessionTypeEnum] = {
    StageEnum.FIRST_INTERVIEW: SessionTypeEnum.FIRST,
    StageEnum.SECOND_INTERVIEW: SessionTypeEnum.SECOND,
    StageEnum.FINAL_INTERVIEW: SessionTypeEnum.FINAL,
}

# AI /chat·/summarize 모두 LLM 호출이라 넉넉히 잡는다.
_AI_TIMEOUT_SECONDS = 90.0


def _get_owned_application(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
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


def _get_owned_session(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> SessionModel:
    # 세션 -> 지원현황 -> 사용자로 소유권을 검증 (남의 회고 세션 접근 차단)
    session = (
        db.query(SessionModel)
        .join(Application, SessionModel.application_id == Application.application_id)
        .filter(
            SessionModel.session_id == session_id,
            Application.user_id == user_id,
        )
        .first()
    )
    if not session:
        raise SessionNotFoundError()
    return session


def _next_sequence(db: Session, session_id: uuid.UUID) -> int:
    current = (
        db.query(func.max(Chat.sequence))
        .filter(Chat.session_id == session_id)
        .scalar()
    )
    return (current or 0) + 1


def _chat_ai(session_id: uuid.UUID, user_message: str, state: dict) -> tuple[str, dict]:
    """AI 서버의 POST /chat을 호출해 (ai_response, updated_state)를 받아온다.

    백엔드는 state 내용을 해석하지 않고 그대로 넘기고, 응답의 updated_state를 그대로 저장한다.
    """
    try:
        with httpx.Client(timeout=_AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_SERVER_URL}/chat",
                json={
                    "session_id": str(session_id),
                    "user_message": user_message,
                    "state": state,
                },
            )
            response.raise_for_status()
            data = response.json()
        return data["ai_response"], data["updated_state"]
    except httpx.HTTPStatusError as exc:
        # AI 서버가 4xx/5xx를 반환한 경우 실제 상태코드/본문을 로그로 남긴다 (502 뒤에 원인이 가려지지 않도록).
        logger.error(
            "AI /chat 실패: status=%s body=%s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise AIServerError()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        # 연결 실패/타임아웃/JSON 파싱 실패/응답 키 누락 등
        logger.error("AI /chat 호출 실패: %r", exc)
        raise AIServerError()


def _summarize_ai(session_id: uuid.UUID, history: list) -> dict:
    """AI 서버의 POST /summarize를 호출해 회고 분석 결과를 받아온다."""
    try:
        with httpx.Client(timeout=_AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_SERVER_URL}/summarize",
                json={"session_id": str(session_id), "history": history},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "AI /summarize 실패: status=%s body=%s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise AIServerError()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("AI /summarize 호출 실패: %r", exc)
        raise AIServerError()


def start_retrospect(
    db: Session, user_id: uuid.UUID, body: RetrospectCreateRequest
) -> tuple[SessionModel, str]:
    """회고 세션을 시작한다. 게이팅 검증 → 세션 생성 → AI 첫 인사 수신."""
    application = _get_owned_application(db, user_id, body.application_id)

    session_type = _STAGE_TO_TYPE.get(application.stage)
    if session_type is None or application.status != ApplicationStatusEnum.COMPLETED:
        raise RetrospectNotAllowedError()

    # 면접 단계당 회고 1개 (이미 있으면 GET으로 이어가기)
    already_exists = (
        db.query(SessionModel.session_id)
        .filter(
            SessionModel.application_id == application.application_id,
            SessionModel.type == session_type,
        )
        .first()
    )
    if already_exists:
        raise RetrospectAlreadyExistsError()

    # 면접 난이도/메모는 지원현황에 저장한다. (AI /chat 계약에 해당 필드가 없어 AI로는 전달하지 않음)
    application.level = body.level
    if body.memo is not None:
        application.memo = body.memo

    initial_state = {
        "stage": SessionStageEnum.FACT.value,
        "stage_turn_count": 0,
        "total_turn_count": 0,
        "company": application.company_name,
        "role": application.position,
        "rejection_stage": session_type.value,
        "hypothesis": "",
        "self_blame_count": 0,
        "history": [],
    }

    session = SessionModel(
        application_id=application.application_id,
        type=session_type,
        stage=SessionStageEnum.FACT,
        status=SessionStatusEnum.IN_PROGRESS,
        ai_state=initial_state,
    )
    db.add(session)
    db.flush()  # session_id 확보 (AI /chat에 넘겨야 함)

    # 첫 턴(오프닝)은 빈 user_message로 호출하면 AI가 먼저 인사 메시지를 생성한다. (AI API v2)
    ai_response, updated_state = _chat_ai(session.session_id, "", initial_state)

    db.add(
        Chat(
            session_id=session.session_id,
            sender=SenderEnum.AI,
            message=ai_response,
            sequence=1,
        )
    )
    session.ai_state = updated_state
    session.stage = SessionStageEnum(updated_state.get("stage", SessionStageEnum.FACT.value))

    db.commit()
    db.refresh(session)
    return session, ai_response


def send_message(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID, message: str
) -> tuple[SessionModel, str, bool]:
    """대화 한 턴. AI /chat 호출 후 사용자/AI 메시지를 함께 저장한다."""
    session = _get_owned_session(db, user_id, session_id)
    if session.status != SessionStatusEnum.IN_PROGRESS:
        raise RetrospectNotInProgressError()
    # 대화가 DONE에 도달하면 더 이상 채팅을 받지 않는다. 이후에는 summarize로 넘어가야 한다.
    if session.stage == SessionStageEnum.DONE:
        raise RetrospectAlreadyDoneError()

    # AI 호출이 성공한 경우에만 두 메시지를 영속화한다 (실패 시 빈 사용자 메시지가 남지 않도록).
    ai_response, updated_state = _chat_ai(session.session_id, message, session.ai_state)

    sequence = _next_sequence(db, session.session_id)
    db.add(
        Chat(
            session_id=session.session_id,
            sender=SenderEnum.USER,
            message=message,
            sequence=sequence,
        )
    )
    db.add(
        Chat(
            session_id=session.session_id,
            sender=SenderEnum.AI,
            message=ai_response,
            sequence=sequence + 1,
        )
    )
    session.ai_state = updated_state
    session.stage = SessionStageEnum(updated_state.get("stage", session.stage.value))

    db.commit()
    db.refresh(session)

    is_done = session.stage == SessionStageEnum.DONE
    return session, ai_response, is_done


def summarize_retrospect(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[SessionModel, InterviewAnalysis]:
    """DONE 단계 도달 후 AI /summarize로 분석을 생성/조회한다. (멱등)"""
    session = _get_owned_session(db, user_id, session_id)
    if session.stage != SessionStageEnum.DONE:
        raise RetrospectNotDoneError()

    existing = (
        db.query(InterviewAnalysis)
        .filter(InterviewAnalysis.session_id == session.session_id)
        .first()
    )
    if existing:
        return session, existing

    history = (session.ai_state or {}).get("history", [])
    result = _summarize_ai(session.session_id, history)

    # AI API v2는 6개 분석 항목을 analysis 객체로 중첩해 반환한다.
    # 서버 전환기 동안 v1(평면) 응답도 받아들이도록 관대하게 파싱한다.
    # (v2 전환이 끝나면 result["analysis"]로 단순화 가능)
    payload = result.get("analysis") or result

    analysis = InterviewAnalysis(
        session_id=session.session_id,
        summary=payload.get("summary"),
        hypothesis=payload.get("hypothesis"),
        strengths=payload.get("strengths"),
        weaknesses=payload.get("weaknesses"),
        gap_analysis=payload.get("gap_analysis"),
        actions=payload.get("actions"),
    )
    db.add(analysis)

    if session.status != SessionStatusEnum.COMPLETED:
        session.status = SessionStatusEnum.COMPLETED
        session.ended_at = func.now()

    db.commit()
    db.refresh(analysis)
    db.refresh(session)
    return session, analysis


def get_retrospect(
    db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[SessionModel, list[Chat], Optional[InterviewAnalysis]]:
    """세션 메타 + 전체 대화 이력 + (있으면) 분석 결과를 조회한다."""
    session = _get_owned_session(db, user_id, session_id)
    chats = (
        db.query(Chat)
        .filter(Chat.session_id == session.session_id)
        .order_by(Chat.sequence)
        .all()
    )
    analysis = (
        db.query(InterviewAnalysis)
        .filter(InterviewAnalysis.session_id == session.session_id)
        .first()
    )
    return session, chats, analysis


def list_retrospects(
    db: Session, user_id: uuid.UUID, application_id: uuid.UUID
) -> list[SessionModel]:
    """지원현황에 속한 회고 세션 목록을 조회한다 (resume용)."""
    application = _get_owned_application(db, user_id, application_id)
    return (
        db.query(SessionModel)
        .filter(SessionModel.application_id == application.application_id)
        .order_by(SessionModel.started_at)
        .all()
    )
