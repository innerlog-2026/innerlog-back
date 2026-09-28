from typing import Optional

from pydantic import BaseModel, Field

from app.models.application import StageEnum
from app.models.session import WeaknessTagEnum


class WeaknessKeywordItem(BaseModel):
    keyword: WeaknessTagEnum = Field(..., description="보완점 태그", examples=["구체성 부족"])
    count: int = Field(..., description="해당 태그가 나온 완료 회고 수", examples=[3])


class StageResultCountItem(BaseModel):
    stage: StageEnum = Field(..., description="전형 단계", examples=["1차면접"])
    pass_count: int = Field(..., description="해당 단계 합격 수", examples=[1])
    fail_count: int = Field(..., description="해당 단계 탈락 수", examples=[2])
    total_count: int = Field(
        ..., description="해당 단계에 도달한 지원 수 (진행중 + 합격 + 탈락)", examples=[4]
    )


class DashboardResponse(BaseModel):
    application_count: int = Field(..., description="지원 횟수 (전체 지원 현황 수)", examples=[2])
    completed_retrospect_count: int = Field(
        ..., description="완료된 회고 수 (요약까지 완료된 회고 세션 수)", examples=[0]
    )
    self_blame_count: int = Field(
        ..., description="자기비난 감지 횟수 (전체 회고 대화에서 감지된 누적 횟수)", examples=[0]
    )
    most_failed_stage: Optional[StageEnum] = Field(
        None,
        description="많이 막히는 단계 (탈락이 가장 많은 전형 단계). 탈락 기록이 없으면 null",
        examples=["최종면접"],
    )
    weakness_keywords: list[WeaknessKeywordItem] = Field(
        ...,
        description="반복 보완 키워드 (완료 회고에서 나온 보완점 태그 중 많이 나온 순 상위 3개). "
        "나온 태그가 3개 미만이면 그 수만큼, 완료 회고가 없으면 빈 배열",
    )
    stage_results: list[StageResultCountItem] = Field(
        ..., description="전형 단계별 합격 현황 (도달한 지원이 있는 단계만, 전형 순서대로)"
    )
