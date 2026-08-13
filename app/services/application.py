import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationNotFoundError
from app.models.application import Application, ApplicationStage, StageEnum, StageStatusEnum
from app.schemas.application import ApplicationCreateRequest

PAGE_SIZE = 5


def _get_owned_application(db: Session, user_id: uuid.UUID, application_id: uuid.UUID) -> Application:
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


def update_stage_result(
    db: Session,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    stage: StageEnum,
    status: StageStatusEnum,
) -> ApplicationStage:
    # (application, stage)별 상태를 upsert. '대기'는 저장하지 않으므로 진행중/합격/탈락만 들어온다.
    application = _get_owned_application(db, user_id, application_id)

    record = (
        db.query(ApplicationStage)
        .filter(
            ApplicationStage.application_id == application.application_id,
            ApplicationStage.stage == stage,
        )
        .first()
    )
    if record:
        record.status = status
    else:
        record = ApplicationStage(
            application_id=application.application_id,
            stage=stage,
            status=status,
        )
        db.add(record)

    # 현재 진행 단계 포인터 동기화 (회고/스피치 게이팅이 Application.stage를 읽는다)
    application.stage = stage

    db.commit()
    db.refresh(record)
    return record
