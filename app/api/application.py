import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.application import (
    create_application_docs,
    get_application_detail_docs,
    list_applications_docs,
    update_stage_result_docs,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationResponse,
    StageResultResponse,
    StageResultUpdateRequest,
    TimelineStageItem,
)
from app.services import application as application_service
from app.services.application import PAGE_SIZE

router = APIRouter(prefix="/applications", tags=["Application"])


@router.post("", response_model=ApplicationResponse, status_code=201, **create_application_docs)
def create_application(
    body: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return application_service.create_application(db, current_user.user_id, body)


@router.get("", response_model=ApplicationListResponse, **list_applications_docs)
def list_applications(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total_count = application_service.list_applications(db, current_user.user_id, page)
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    return ApplicationListResponse(
        items=[ApplicationListItem.model_validate(item) for item in items],
        page=page,
        size=PAGE_SIZE,
        total_count=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
    )


@router.get("/{application_id}", response_model=ApplicationDetailResponse, **get_application_detail_docs)
def get_application_detail(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    (
        application,
        timeline,
        current_status,
        first_done,
        second_done,
        speech_created,
        speech_available,
    ) = application_service.get_application_detail(db, current_user.user_id, application_id)
    return ApplicationDetailResponse(
        application_id=application.application_id,
        company_name=application.company_name,
        position=application.position,
        current_stage=application.stage,
        status=current_status,
        first_interview_retrospect_completed=first_done,
        second_interview_retrospect_completed=second_done,
        speech_practice_created=speech_created,
        speech_practice_available=speech_available,
        timeline=[TimelineStageItem(stage=stage, status=status) for stage, status in timeline],
    )


@router.patch(
    "/{application_id}/stage-result",
    response_model=StageResultResponse,
    **update_stage_result_docs,
)
def update_stage_result(
    application_id: uuid.UUID,
    body: StageResultUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = application_service.update_stage_result(
        db, current_user.user_id, application_id, body.stage, body.status
    )
    return StageResultResponse.model_validate(record)
