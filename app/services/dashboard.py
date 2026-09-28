import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStage, StageEnum, StageStatusEnum
from app.models.session import (
    InterviewAnalysis,
    Session as SessionModel,
    SessionStatusEnum,
    WeaknessTagEnum,
)

WEAKNESS_KEYWORD_LIMIT = 3


@dataclass
class StageResultCount:
    stage: StageEnum
    pass_count: int
    fail_count: int
    total_count: int  # 진행중 + 합격 + 탈락 (대기는 행이 없어 제외됨)


def _count_stage_results(db: Session, user_id: uuid.UUID) -> list[StageResultCount]:
    """본인 지원 현황의 타임라인 행을 (단계, 상태)별로 집계함. 도달한 지원이 없는 단계는 제외함."""
    rows = (
        db.query(ApplicationStage.stage, ApplicationStage.status, func.count())
        .join(Application, ApplicationStage.application_id == Application.application_id)
        .filter(Application.user_id == user_id)
        .group_by(ApplicationStage.stage, ApplicationStage.status)
        .all()
    )
    counts = {(stage, status): count for stage, status, count in rows}

    results = []
    for stage in StageEnum:
        total = sum(counts.get((stage, status), 0) for status in StageStatusEnum)
        if total == 0:
            continue
        results.append(
            StageResultCount(
                stage=stage,
                pass_count=counts.get((stage, StageStatusEnum.PASS), 0),
                fail_count=counts.get((stage, StageStatusEnum.FAIL), 0),
                total_count=total,
            )
        )
    return results


def _most_failed_stage(stage_results: list[StageResultCount]) -> Optional[StageEnum]:
    """탈락 수가 가장 많은 단계를 반환함.

    동률이면 합격 수가 적은 단계, 그래도 같으면 뒤 단계를 고름. 탈락 기록이 없으면 None.
    """
    failed = [result for result in stage_results if result.fail_count > 0]
    if not failed:
        return None
    # max 는 동률 시 먼저 만난 값을 반환하므로 역순으로 순회해 뒤 단계가 우선되게 함.
    return max(reversed(failed), key=lambda result: (result.fail_count, -result.pass_count)).stage


def _count_weakness_keywords(db: Session, user_id: uuid.UUID) -> list[tuple[WeaknessTagEnum, int]]:
    """본인 회고 분석 결과의 보완점 태그별로 해당 태그가 나온 분석 수를 집계해 상위 태그만 반환함.

    고정 태그가 아닌 값(자유문장 weaknesses)은 제외함. 많이 나온 순, 동률이면 태그 정의 순으로 정렬해
    WEAKNESS_KEYWORD_LIMIT 개까지 자름.
    """
    tag_rows = (
        db.query(
            InterviewAnalysis.interview_analysis_id,
            func.unnest(InterviewAnalysis.weaknesses).label("tag"),
        )
        .join(SessionModel, InterviewAnalysis.session_id == SessionModel.session_id)
        .join(Application, SessionModel.application_id == Application.application_id)
        .filter(Application.user_id == user_id)
        .subquery()
    )
    # 한 분석에 같은 태그가 중복돼도 1회로 세도록 분석 ID 기준으로 셈.
    rows = (
        db.query(tag_rows.c.tag, func.count(func.distinct(tag_rows.c.interview_analysis_id)))
        .filter(tag_rows.c.tag.in_([tag.value for tag in WeaknessTagEnum]))
        .group_by(tag_rows.c.tag)
        .all()
    )
    tag_order = list(WeaknessTagEnum)
    keywords = [(WeaknessTagEnum(tag), count) for tag, count in rows]
    keywords.sort(key=lambda item: (-item[1], tag_order.index(item[0])))
    return keywords[:WEAKNESS_KEYWORD_LIMIT]


def get_dashboard(
    db: Session, user_id: uuid.UUID
) -> tuple[
    int, int, int, Optional[StageEnum], list[tuple[WeaknessTagEnum, int]], list[StageResultCount]
]:
    """대시보드 지표를 조회 시점 데이터로 집계함."""
    application_count = (
        db.query(func.count(Application.application_id))
        .filter(Application.user_id == user_id)
        .scalar()
    )

    user_sessions = (
        db.query(SessionModel)
        .join(Application, SessionModel.application_id == Application.application_id)
        .filter(Application.user_id == user_id)
    )
    completed_retrospect_count = (
        user_sessions.filter(SessionModel.status == SessionStatusEnum.COMPLETED)
        .with_entities(func.count(SessionModel.session_id))
        .scalar()
    )
    # ai_state.self_blame_count 는 AI 서버가 세션 내에서 누적하는 값이므로 세션별 값을 합산함.
    self_blame_count = user_sessions.with_entities(
        func.coalesce(func.sum(SessionModel.ai_state["self_blame_count"].as_integer()), 0)
    ).scalar()

    stage_results = _count_stage_results(db, user_id)

    return (
        application_count,
        completed_retrospect_count,
        self_blame_count,
        _most_failed_stage(stage_results),
        _count_weakness_keywords(db, user_id),
        stage_results,
    )
