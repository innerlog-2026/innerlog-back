import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationNotFoundError, PastStageRevertError
from app.models.application import (
    Application,
    ApplicationStage,
    ApplicationStatusEnum,
    StageEnum,
    StageStatusEnum,
)
from app.models.session import Session as SessionModel, SessionStatusEnum, SessionTypeEnum
from app.schemas.application import (
    ApplicationCreateRequest,
    RetrospectStatusEnum,
    TimelineStatusEnum,
)
from app.services.retrospect import available_retrospect_types, retrospect_type_for_stage
from app.services.speech import is_speech_practice_available, is_speech_practice_created

PAGE_SIZE = 5


@dataclass
class RetrospectFlags:
    available: bool  # 현재 전형 단계에서 회고 시작 허용
    created: bool  # 회고 세션 존재 (대화 중 포함)
    completed: bool  # 회고 세션 COMPLETED (요약 완료)


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


def list_applications(
    db: Session, user_id: uuid.UUID, page: int
) -> tuple[list[Application], int, dict[uuid.UUID, Optional[RetrospectStatusEnum]]]:
    # 본인 소유 지원 현황만 최신순으로 한 페이지(PAGE_SIZE)씩 조회
    base = db.query(Application).filter(Application.user_id == user_id)
    total_count = base.count()
    items = (
        base.order_by(Application.created_at.desc(), Application.application_id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    # 페이지 항목의 회고 세션을 한 번에 조회해 현재 단계 회고 상태를 판별함.
    sessions = (
        db.query(SessionModel.application_id, SessionModel.type, SessionModel.status)
        .filter(SessionModel.application_id.in_([item.application_id for item in items]))
        .all()
    )
    session_status_by_key = {
        (application_id, session_type): status for application_id, session_type, status in sessions
    }
    retrospect_statuses: dict[uuid.UUID, Optional[RetrospectStatusEnum]] = {}
    for item in items:
        session_type = retrospect_type_for_stage(item.stage)
        session_status = session_status_by_key.get((item.application_id, session_type))
        if session_type is None:
            # 면접 단계가 아니면 회고 대상이 아니므로 null로 둠.
            retrospect_statuses[item.application_id] = None
        elif session_status is None:
            retrospect_statuses[item.application_id] = RetrospectStatusEnum.NOT_STARTED
        elif session_status is SessionStatusEnum.COMPLETED:
            retrospect_statuses[item.application_id] = RetrospectStatusEnum.COMPLETED
        else:
            # 세션이 있으면 새로 시작할 수 없으므로 완료 전 상태는 모두 회고중으로 봄.
            retrospect_statuses[item.application_id] = RetrospectStatusEnum.IN_PROGRESS
    return items, total_count, retrospect_statuses


def update_stage_result(
    db: Session,
    user_id: uuid.UUID,
    application_id: uuid.UUID,
    stage: StageEnum,
    status: StageStatusEnum,
) -> ApplicationStage:
    # (application, stage)별 상태를 upsert. '대기'는 저장하지 않으므로 진행중/합격/탈락만 들어온다.
    application = _get_owned_application(db, user_id, application_id)

    pipeline = list(StageEnum)
    target_index = pipeline.index(stage)
    current_index = None if application.stage is None else pipeline.index(application.stage)
    is_forward = current_index is None or target_index > current_index
    is_past = current_index is not None and target_index < current_index

    # 포인터보다 앞 단계는 진행중일 수 없으므로 지난 단계를 진행중으로 되돌리는 요청은 거절함.
    if is_past and status is StageStatusEnum.IN_PROGRESS:
        raise PastStageRevertError()

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

    # 포인터는 뒤 단계 요청 시 전진하고, 지난 단계 탈락 정정 시에만 그 단계로 후퇴함.
    # 지난 단계 합격 정정은 타임라인만 갱신함 (회고/스피치 게이팅이 Application.stage를 읽음).
    if is_forward:
        application.stage = stage

        # 포인터 전진 시 새 단계보다 앞의 진행중 단계는 통과한 것으로 보고 합격으로 정리함.
        # 탈락은 사용자 입력 결과라 유지하고, 행이 없는 단계(대기 = 건너뛴 단계)는 만들지 않음.
        earlier_in_progress = (
            db.query(ApplicationStage)
            .filter(
                ApplicationStage.application_id == application.application_id,
                ApplicationStage.stage.in_(pipeline[:target_index]),
                ApplicationStage.status == StageStatusEnum.IN_PROGRESS,
            )
            .all()
        )
        for earlier in earlier_in_progress:
            earlier.status = StageStatusEnum.PASS
    elif is_past and status is StageStatusEnum.FAIL:
        application.stage = stage

        # 탈락한 단계 이후로는 진행할 수 없으므로 뒤 단계 행을 삭제해 대기로 되돌림.
        later_rows = (
            db.query(ApplicationStage)
            .filter(
                ApplicationStage.application_id == application.application_id,
                ApplicationStage.stage.in_(pipeline[target_index + 1 :]),
            )
            .all()
        )
        for later in later_rows:
            db.delete(later)

    # 지원 현황 상태는 포인터 단계의 타임라인 값에서 파생 (합격/탈락 = 완료)
    db.flush()
    application.status = _derive_status(db, application)

    db.commit()
    db.refresh(record)
    return record


def get_application_detail(db: Session, user_id: uuid.UUID, application_id: uuid.UUID):
    # 상세 + 타임라인(고정 파이프라인) + 면접 회고 활성/생성/완료 여부 + 스피치 연습 생성/활성 여부
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

    # 회고 세션이 있으면 '생성', COMPLETED면 '완료'
    sessions = (
        db.query(SessionModel.type, SessionModel.status)
        .filter(SessionModel.application_id == application.application_id)
        .all()
    )
    created_types = {session_type for session_type, _ in sessions}
    completed_types = {
        session_type
        for session_type, status in sessions
        if status == SessionStatusEnum.COMPLETED
    }
    available_types = available_retrospect_types(application)
    retrospects = {
        session_type: RetrospectFlags(
            available=session_type in available_types,
            created=session_type in created_types,
            completed=session_type in completed_types,
        )
        for session_type in SessionTypeEnum
    }

    speech_created = is_speech_practice_created(db, application)
    speech_available = is_speech_practice_available(db, application)

    return application, timeline, current_status, retrospects, speech_created, speech_available
