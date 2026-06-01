import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonalStatementItem(BaseModel):
    question: str = Field(..., description="자기소개서 문항", examples=["지원 동기를 작성해주세요."])
    content: str = Field(..., description="자기소개서 내용", examples=["저는 백엔드 개발에 관심이 많아..."])


class SpeechPracticeCreateReq(BaseModel):
    application_id: uuid.UUID = Field(..., description="지원 현황 ID")
    company_name: str = Field(..., description="회사명", examples=["카카오"])
    position: str = Field(..., description="지원 직무", examples=["백엔드 개발자"])
    personal_statements: list[PersonalStatementItem] = Field(
        ..., description="자기소개서 문항/내용 목록", min_length=1
    )


class QuestionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: uuid.UUID
    question: str
    category: Optional[str]
    sequence: Optional[int]


class SpeechPracticeCreateResponse(BaseModel):
    application_id: uuid.UUID
    questions: list[QuestionItem]
