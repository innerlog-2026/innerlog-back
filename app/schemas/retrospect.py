import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.application import LevelEnum
from app.models.session import (
    SenderEnum,
    SessionStageEnum,
    SessionStatusEnum,
    SessionTypeEnum,
)


# --- 회고 시작 ---


class RetrospectCreateRequest(BaseModel):
    application_id: uuid.UUID = Field(..., description="회고할 지원 현황 ID")
    level: LevelEnum = Field(
        ..., description="면접 체감 난이도 (HARD / MEDIUM_HIGH / MEDIUM_LOW / EASY)", examples=["MEDIUM_HIGH"]
    )
    memo: Optional[str] = Field(None, description="면접에 대한 간단한 메모 (선택)", examples=["기술 질문이 많았음"])


class RetrospectCreateResponse(BaseModel):
    session_id: uuid.UUID
    application_id: uuid.UUID
    type: SessionTypeEnum = Field(..., description="회고 대상 면접 단계", examples=["1차면접"])
    stage: SessionStageEnum = Field(..., description="현재 대화 단계", examples=["FACT"])
    status: SessionStatusEnum
    message: str = Field(..., description="첫 AI 인사 메시지", examples=["프론트엔드 AI회고를 시작할게요. 먼저 사실을 확인할게요. 면접에서 주로 어떤 유형의 질문을 물어보았나요?"])
    started_at: datetime


# --- 대화 한 턴 ---


class RetrospectChatRequest(BaseModel):
    message: str = Field(..., description="사용자 답변", examples=["주로 직무 관련 질문을 물어봤어요."])


class RetrospectChatResponse(BaseModel):
    session_id: uuid.UUID
    message: str = Field(..., description="AI 답변")
    stage: SessionStageEnum = Field(..., description="이번 턴 이후의 대화 단계", examples=["INTERPRETATION"])
    is_done: bool = Field(..., description="대화가 DONE 단계에 도달했는지 여부 (true면 summarize 호출 가능)")


# --- 조회용 공통 ---


class ChatItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_id: uuid.UUID
    sender: SenderEnum = Field(..., description="발화자 (AI / USER)")
    message: str
    sequence: int
    created_at: datetime


class InterviewAnalysisResult(BaseModel):
    summary: Optional[str] = Field(None, description="면접 총평")
    hypothesis: Optional[str] = Field(None, description="탈락/아쉬움 원인 가설")
    strengths: Optional[str] = Field(None, description="잘한 점")
    weaknesses: list[str] = Field(default_factory=list, description="아쉬운 점")
    gap_analysis: Optional[str] = Field(None, description="갭 분석")
    actions: list[str] = Field(default_factory=list, description="개선 가이드 (다음 지원 시 액션)")


# --- 분석 결과 (summarize) ---


class RetrospectSummaryResponse(BaseModel):
    session_id: uuid.UUID
    company: str = Field(..., description="회사명")
    role: str = Field(..., description="지원 직무")
    interview_type: SessionTypeEnum = Field(..., description="회고 대상 면접 단계")
    analysis: InterviewAnalysisResult


# --- 세션 상세 ---


class RetrospectDetailResponse(BaseModel):
    session_id: uuid.UUID
    application_id: uuid.UUID
    type: SessionTypeEnum
    stage: SessionStageEnum
    status: SessionStatusEnum
    started_at: datetime
    ended_at: Optional[datetime]
    chats: list[ChatItem]
    analysis: Optional[InterviewAnalysisResult] = Field(None, description="DONE 후 생성된 분석 결과 (없으면 null)")


# --- 지원현황별 회고 목록 (resume용) ---


class RetrospectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    type: SessionTypeEnum
    stage: SessionStageEnum
    status: SessionStatusEnum
    started_at: datetime
    ended_at: Optional[datetime]


class RetrospectListResponse(BaseModel):
    application_id: uuid.UUID
    sessions: list[RetrospectListItem]
