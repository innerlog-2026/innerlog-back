import enum
import uuid
from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationStatusEnum, StageEnum, StageStatusEnum


class TimelineStatusEnum(str, enum.Enum):
    # 응답 전용: 저장 상태(진행중/합격/탈락) + 파생 상태(대기=미도달 단계)
    PENDING = "대기"
    IN_PROGRESS = "진행중"
    PASS = "합격"
    FAIL = "탈락"


class ApplicationCreateRequest(BaseModel):
    company_name: str = Field(..., description="회사명", examples=["네이버"])
    position: str = Field(..., description="지원 직무", examples=["백엔드 개발자"])
    stage: Optional[StageEnum] = Field(None, description="전형 단계", examples=["서류전형"])
    date: Optional[date_type] = Field(None, description="지원 날짜", examples=["2026-04-15"])
    status: ApplicationStatusEnum = Field(
        ApplicationStatusEnum.IN_PROGRESS,
        description="전형 단계의 상태 (IN_PROGRESS = 결과 대기 / COMPLETED = 결과 나옴)",
    )


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    position: str
    stage: Optional[StageEnum]
    date: Optional[date_type]
    status: ApplicationStatusEnum
    created_at: datetime
    updated_at: datetime


class ApplicationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID = Field(..., description="지원 현황 ID")
    company_name: str = Field(..., description="기업명", examples=["토스 뱅크"])
    stage: Optional[StageEnum] = Field(None, description="전형 단계", examples=["서류전형"])
    status: ApplicationStatusEnum = Field(
        ..., description="해당 전형 단계의 상태 (IN_PROGRESS = 결과 대기 / COMPLETED = 합격 또는 탈락)"
    )


class ApplicationListResponse(BaseModel):
    items: list[ApplicationListItem] = Field(..., description="지원 현황 목록 (최신순)")
    page: int = Field(..., description="현재 페이지 번호 (1부터)", examples=[1])
    size: int = Field(..., description="페이지당 항목 수", examples=[5])
    total_count: int = Field(..., description="전체 지원 현황 수", examples=[12])
    total_pages: int = Field(..., description="전체 페이지 수", examples=[3])
    has_next: bool = Field(..., description="다음 페이지 존재 여부")


class StageResultUpdateRequest(BaseModel):
    stage: StageEnum = Field(..., description="현재 진행 단계", examples=["1차면접"])
    status: StageStatusEnum = Field(
        ..., description="해당 단계 상태 (진행중 / 합격 / 탈락). '대기'는 저장하지 않음", examples=["합격"]
    )


class StageResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    stage: StageEnum
    status: StageStatusEnum
    updated_at: datetime


class TimelineStageItem(BaseModel):
    stage: StageEnum = Field(..., description="전형 단계", examples=["1차면접"])
    status: TimelineStatusEnum = Field(
        ..., description="단계 상태 (대기 / 진행중 / 합격 / 탈락). 미도달 단계는 대기", examples=["진행중"]
    )


class ApplicationDetailResponse(BaseModel):
    application_id: uuid.UUID
    company_name: str = Field(..., description="기업명", examples=["토스뱅크"])
    position: str = Field(..., description="직무", examples=["프론트엔드 개발자"])
    current_stage: Optional[StageEnum] = Field(None, description="현재 전형 단계", examples=["1차면접"])
    status: Optional[StageStatusEnum] = Field(
        None, description="현재 전형 단계의 상태 (진행중 / 합격 / 탈락). null = 대기", examples=["진행중"]
    )
    first_interview_retrospect_completed: bool = Field(..., description="1차 면접 회고 완료 여부")
    second_interview_retrospect_completed: bool = Field(..., description="2차 면접 회고 완료 여부")
    speech_practice_created: bool = Field(
        ..., description="스피치 연습 최초 생성 여부 (POST /speech-practices 로 예상 질문이 저장된 적 있음)"
    )
    speech_practice_available: bool = Field(
        ..., description="현재 전형 단계·상태에서 스피치 연습 기능 활성화 여부"
    )
    timeline: list[TimelineStageItem] = Field(
        ..., description="전형 진행 단계 타임라인 (고정 파이프라인 전체, 순서대로). 미도달 단계는 대기"
    )
