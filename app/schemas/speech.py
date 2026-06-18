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


class QuestionProgressItem(BaseModel):
    question_id: uuid.UUID
    question: str
    category: Optional[str]
    sequence: Optional[int]
    is_practiced: bool = Field(..., description="연습 완료 여부 (제출 이력 존재 여부)")


class SpeechPracticeQuestionListResponse(BaseModel):
    application_id: uuid.UUID
    total_count: int = Field(..., description="전체 질문 수")
    practiced_count: int = Field(..., description="연습한 질문 수")
    questions: list[QuestionProgressItem]


class SpeechPracticeQuestionGenerateResponse(BaseModel):
    application_id: uuid.UUID
    added_count: int = Field(..., description="이번에 새로 추가된 질문 수 (중복 제외)")
    questions: list[QuestionItem] = Field(..., description="새로 추가된 질문 목록")
