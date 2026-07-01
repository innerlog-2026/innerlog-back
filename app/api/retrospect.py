import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.retrospect import (
    chat_retrospect_docs,
    get_retrospect_docs,
    list_retrospects_docs,
    start_retrospect_docs,
    summarize_retrospect_docs,
)
from app.core.database import get_db
from app.models.session import InterviewAnalysis
from app.models.user import User
from app.schemas.retrospect import (
    ChatItem,
    InterviewAnalysisResult,
    RetrospectChatRequest,
    RetrospectChatResponse,
    RetrospectCreateRequest,
    RetrospectCreateResponse,
    RetrospectDetailResponse,
    RetrospectListItem,
    RetrospectListResponse,
    RetrospectSummaryResponse,
)
from app.services import retrospect as retrospect_service

router = APIRouter(prefix="/retrospects", tags=["Interview Retrospect"])


def _to_analysis_result(
    analysis: Optional[InterviewAnalysis],
) -> Optional[InterviewAnalysisResult]:
    if analysis is None:
        return None
    return InterviewAnalysisResult(
        summary=analysis.summary,
        hypothesis=analysis.hypothesis,
        strengths=analysis.strengths,
        weaknesses=analysis.weaknesses or [],
        gap_analysis=analysis.gap_analysis,
        actions=analysis.actions or [],
    )


@router.post("", response_model=RetrospectCreateResponse, status_code=201, **start_retrospect_docs)
def start_retrospect(
    body: RetrospectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session, message = retrospect_service.start_retrospect(db, current_user.user_id, body)
    return RetrospectCreateResponse(
        session_id=session.session_id,
        application_id=session.application_id,
        type=session.type,
        stage=session.stage,
        status=session.status,
        message=message,
        started_at=session.started_at,
    )


@router.get("", response_model=RetrospectListResponse, **list_retrospects_docs)
def list_retrospects(
    application_id: uuid.UUID = Query(..., description="회고 세션을 조회할 지원 현황 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = retrospect_service.list_retrospects(db, current_user.user_id, application_id)
    return RetrospectListResponse(
        application_id=application_id,
        sessions=[RetrospectListItem.model_validate(session) for session in sessions],
    )


@router.post("/{session_id}/chat", response_model=RetrospectChatResponse, **chat_retrospect_docs)
def chat_retrospect(
    session_id: uuid.UUID,
    body: RetrospectChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session, message, is_done = retrospect_service.send_message(
        db, current_user.user_id, session_id, body.message
    )
    return RetrospectChatResponse(
        session_id=session.session_id,
        message=message,
        stage=session.stage,
        is_done=is_done,
    )


@router.post(
    "/{session_id}/summarize",
    response_model=RetrospectSummaryResponse,
    **summarize_retrospect_docs,
)
def summarize_retrospect(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session, analysis = retrospect_service.summarize_retrospect(
        db, current_user.user_id, session_id
    )
    return RetrospectSummaryResponse(
        session_id=session.session_id,
        company=session.application.company_name,
        role=session.application.position,
        interview_type=session.type,
        analysis=_to_analysis_result(analysis),
    )


@router.get("/{session_id}", response_model=RetrospectDetailResponse, **get_retrospect_docs)
def get_retrospect(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session, chats, analysis = retrospect_service.get_retrospect(
        db, current_user.user_id, session_id
    )
    return RetrospectDetailResponse(
        session_id=session.session_id,
        application_id=session.application_id,
        type=session.type,
        stage=session.stage,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        chats=[ChatItem.model_validate(chat) for chat in chats],
        analysis=_to_analysis_result(analysis),
    )
