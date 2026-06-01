import uuid
from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationStatusEnum, StageEnum


class ApplicationCreateRequest(BaseModel):
    company_name: str = Field(..., description="회사명", examples=["네이버"])
    position: str = Field(..., description="지원 직무", examples=["백엔드 개발자"])
    stage: Optional[StageEnum] = Field(None, description="전형 단계", examples=["서류전형"])
    date: Optional[date_type] = Field(None, description="지원 날짜", examples=["2026-04-15"])
    status: ApplicationStatusEnum = Field(
        ApplicationStatusEnum.PREPARING, description="진행 상태 (PREPARING / IN_PROGRESS / COMPLETED)"
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
