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


# --- 스피치 분석 (AI POST /speech-analyze 응답 구조를 그대로 반영) ---


class AcousticResult(BaseModel):
    speed_wpm: Optional[float] = Field(None, description="발화 속도 (어절/분)", examples=[78.0])
    speed_label: Optional[str] = Field(None, examples=["평균(90.14어절/분)보다 느린 편이에요"])
    filler_words: dict[str, int] = Field(default_factory=dict, description="채움말별 횟수", examples=[{"그": 1}])
    silence_count: Optional[int] = Field(None, description="침묵 구간 수")
    duration_sec: Optional[float] = Field(None, description="발화 길이(초)", examples=[86.2])
    word_count: Optional[int] = Field(None, description="어절 수")


class StarItem(BaseModel):
    """STAR 요소 1개 (AI v2: present + comment)."""

    present: bool = False
    comment: Optional[str] = None


class StarScore(BaseModel):
    situation: StarItem = Field(default_factory=StarItem)
    task: StarItem = Field(default_factory=StarItem)
    action: StarItem = Field(default_factory=StarItem)
    result: StarItem = Field(default_factory=StarItem)


class Coherence(BaseModel):
    """두서없음 판정 (AI v2: 객체)."""

    summary: Optional[str] = Field(None, examples=["논리 흐름 양호"])
    detail: Optional[str] = None


class NegativeReframe(BaseModel):
    detected: bool = Field(False, description="약점 노출 표현 감지 여부")
    expressions: list[str] = Field(default_factory=list)
    feedback: Optional[str] = None


class ContentResult(BaseModel):
    question_type: Optional[str] = Field(
        None, description="질문 유형 (행동형 / 의견형 / 기술형 / 가정형)", examples=["행동형"]
    )
    star_score: Optional[StarScore] = Field(
        None, description="STAR 구조 분석. 행동형 질문이 아니면 null"
    )
    coherence: Coherence = Field(default_factory=Coherence)
    keyword_repeat: dict[str, int] = Field(default_factory=dict, description="4회 이상 반복 키워드")
    negative_reframe: NegativeReframe = Field(default_factory=NegativeReframe)
    overall: Optional[str] = Field(None, description="종합 피드백")


class SpeechAnalysisResponse(BaseModel):
    submission_id: uuid.UUID = Field(..., description="생성된 제출 ID")
    question_id: uuid.UUID = Field(..., description="대상 질문 ID")
    acoustic: AcousticResult
    content: ContentResult
