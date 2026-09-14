import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationNotFoundError
from app.models.application import (
    Application,
    ApplicationStage,
    ApplicationStatusEnum,
    StageEnum,
    StageStatusEnum,
)
from app.models.session import Session as SessionModel, SessionStatusEnum, SessionTypeEnum
from app.schemas.application import ApplicationCreateRequest, TimelineStatusEnum
from app.services.speech import is_speech_practice_available, is_speech_practice_created

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


def _derive_status(db: Session, application: Application) -> ApplicationStatusEnum:
    """지원 현황 상태 = 포인터가 가리키는 단계의 타임라인 값을 2값으로 접은 것.

    합격/탈락은 모두 '그 단계가 끝남' 이므로 완료로 접힌다.
    진행중이거나 아직 타임라인 행이 없으면 진행중.
    """
    if application.stage is None:
        return ApplicationStatusEnum.IN_PROGRESS

    stage_status = (
        db.query(ApplicationStage.status)
        .filter(
            ApplicationStage.application_id == application.application_id,
            ApplicationStage.stage == application.stage,
        )
        .scalar()
    )
    if stage_status is None or stage_status is StageStatusEnum.IN_PROGRESS:
        return ApplicationStatusEnum.IN_PROGRESS
    return ApplicationStatusEnum.COMPLETED


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
    db.flush()  # application_id 확보 (아래 단계별 행 FK에 필요)

    # 생성 시 timeline 시딩: 현재 단계까지 도달한 것으로 보고
    # 이전 단계 = 합격 (이후 단계는 대기 = 행 없음)
    # 현재 단계는 status 와 어긋나지 않게 맞춘다. 완료로 등록하면 통과한 것으로 본다
    # (탈락이면 이후 stage-result PATCH 로 정정).
    if body.stage is not None:
        pipeline = list(StageEnum)
        current_index = pipeline.index(body.stage)
        for prev_stage in pipeline[:current_index]:
            db.add(
                ApplicationStage(
                    application_id=application.application_id,
                    stage=prev_stage,
                    status=StageStatusEnum.PASS,
                )
            )
        db.add(
            ApplicationStage(
                application_id=application.application_id,
                stage=body.stage,
                status=(
                    StageStatusEnum.PASS
                    if body.status is ApplicationStatusEnum.COMPLETED
                    else StageStatusEnum.IN_PROGRESS
                ),
            )
        )

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

    # 포인터는 앞으로만 이동. 과거 단계 결과를 정정하는 요청은 타임라인만 갱신하고
    # 포인터를 되돌리지 않는다 (회고/스피치 게이팅이 Application.stage를 읽는다).
    pipeline = list(StageEnum)
    if application.stage is None or pipeline.index(stage) > pipeline.index(application.stage):
        application.stage = stage

    # 지원 현황 상태는 포인터 단계의 타임라인 값에서 파생 (합격/탈락 = 완료)
    db.flush()
    application.status = _derive_status(db, application)

    db.commit()
    db.refresh(record)
    return record


def get_application_detail(db: Session, user_id: uuid.UUID, application_id: uuid.UUID):
    # 상세 + 타임라인(고정 파이프라인) + 1·2차 회고 완료 여부 + 스피치 연습 생성/활성 여부
    application = _get_owned_application(db, user_id, application_id)

    stage_rows = (
        db.query(ApplicationStage)
        .filter(ApplicationStage.application_id == application.application_id)
        .all()
    )
    status_by_stage = {row.stage: row.status for row in stage_rows}
    # 고정 파이프라인 전체를 StageEnum 순서로. 도달하지 않은 단계는 '대기'로 파생(저장은 안 함).
    timeline = []
    for stage in StageEnum:
        stored = status_by_stage.get(stage)
        timeline.append(
            (stage, TimelineStatusEnum[stored.name] if stored else TimelineStatusEnum.PENDING)
        )
    current_status = status_by_stage.get(application.stage)

    # 회고 세션이 COMPLETED면 해당 면접 회고 '완료'
    completed_types = {
        session_type
        for (session_type,) in (
            db.query(SessionModel.type)
            .filter(
                SessionModel.application_id == application.application_id,
                SessionModel.status == SessionStatusEnum.COMPLETED,
            )
            .all()
        )
    }
    first_done = SessionTypeEnum.FIRST in completed_types
    second_done = SessionTypeEnum.SECOND in completed_types

    speech_created = is_speech_practice_created(db, application)
    speech_available = is_speech_practice_available(db, application)

    return (
        application,
        timeline,
        current_status,
        first_done,
        second_done,
        speech_created,
        speech_available,
    )
