from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.application import create_application_docs, list_applications_docs
from app.core.database import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationResponse,
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
