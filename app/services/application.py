import uuid

from sqlalchemy.orm import Session

from app.models.application import Application
from app.schemas.application import ApplicationCreateRequest

PAGE_SIZE = 5


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


def list_applications(db: Session, user_id: uuid.UUID, page: int) -> tuple[list[Application], int]:
    # 본인 소유 지원 현황만 최신순으로 한 페이지(PAGE_SIZE)씩 조회
    base = db.query(Application).filter(Application.user_id == user_id)
    total_count = base.count()
    items = (
        base.order_by(Application.created_at.desc(), Application.application_id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    return items, total_count
