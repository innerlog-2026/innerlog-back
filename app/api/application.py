from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.application import create_application_docs
from app.core.database import get_db
from app.models.user import User
from app.schemas.application import ApplicationCreateRequest, ApplicationResponse
from app.services import application as application_service

router = APIRouter(prefix="/applications", tags=["Application"])


@router.post("", response_model=ApplicationResponse, status_code=201, **create_application_docs)
def create_application(
    body: ApplicationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return application_service.create_application(db, current_user.user_id, body)
