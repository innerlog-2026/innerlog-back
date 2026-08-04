import uuid

from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreateRequest


def create_application(db: Session, user_id: uuid.UUID, body: ApplicationCreateRequest) -> Application:
    application = Application(
        user_id=user_id,
        company_name=body.company_name,
        position=body.position,
        stage=body.stage,
        date=body.date,
        status=body.status,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application
