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


class Baseline(BaseModel):
    """게이지용 기준값 (AI Hub 채용면접 데이터 분포).

    게이지 양 끝은 p5~p95, 보통 범위 띠는 p33~p67, 평균 눈금은 mean.
    """

    mean: Optional[float] = Field(None, description="평균")
    p5: Optional[float] = Field(None, description="하위 5% (게이지 왼쪽 끝)")
    p33: Optional[float] = Field(None, description="하위 33% (보통 범위 시작)")
    p67: Optional[float] = Field(None, description="상위 33% (보통 범위 끝)")
    p95: Optional[float] = Field(None, description="상위 5% (게이지 오른쪽 끝)")
    unit: Optional[str] = Field(None, description="단위. length_baseline 에만 존재", examples=["sec"])
    source: Optional[str] = Field(None, description="기준 데이터 출처", examples=["AI Hub 채용면접 데이터 (ICT 직군)"])
    sample_count: Optional[int] = Field(None, description="표본 수")


class AcousticResult(BaseModel):
    speed_wpm: Optional[float] = Field(None, description="발화 속도 (어절/분)", examples=[78.0])
    speed_label: Optional[str] = Field(None, examples=["평균(90.14어절/분)보다 느린 편이에요"])
    speed_baseline: Optional[Baseline] = Field(
        None, description="말 속도 기준값 (어절/분). 기준값 추가 이전 결과는 null"
    )
    filler_words: dict[str, int] = Field(default_factory=dict, description="채움말별 횟수", examples=[{"그": 1}])
    silence_count: Optional[int] = Field(None, description="침묵 구간 수")
    duration_sec: Optional[float] = Field(None, description="발화 길이(초)", examples=[86.2])
    word_count: Optional[int] = Field(None, description="어절 수")
    length_label: Optional[str] = Field(
        None, description="답변 길이 문구 (p33/p67 기준 3단계)", examples=["평균(89.38초)보다 짧은 편이에요"]
    )
    length_baseline: Optional[Baseline] = Field(
        None, description="답변 시간 기준값 (초). 기준값 추가 이전 결과는 null"
    )


class StarItem(BaseModel):
    """STAR 요소 1개 (AI v2 최종: present + comment).

    비행동형 질문에서는 4개 항목이 모두 {"present": null, "comment": null} 로 온다.
    따라서 present 를 bool 로 못박으면 의견형 응답에서 ValidationError 가 난다.
    """

    present: Optional[bool] = None
    comment: Optional[str] = None


class StarScore(BaseModel):
    # AI v2 최종: 4개 키는 항상 존재하고, 비행동형이면 각 항목의 present/comment 가 null.
    # (구버전 명세처럼 키 자체가 null 로 오는 경우도 흡수하기 위해 Optional 을 유지한다.)
    situation: Optional[StarItem] = None
    task: Optional[StarItem] = None
    action: Optional[StarItem] = None
    result: Optional[StarItem] = None


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
        None,
        description="STAR 구조 분석. 비행동형 질문이면 4개 항목이 모두 "
        '{"present": null, "comment": null} 로 온다',
    )
    coherence: Coherence = Field(default_factory=Coherence)
    keyword_repeat: dict[str, int] = Field(default_factory=dict, description="4회 이상 반복 키워드")
    negative_reframe: NegativeReframe = Field(default_factory=NegativeReframe)
    overall: Optional[str] = Field(
        None,
        deprecated=True,
        description="[deprecated] 종합 피드백. AI v2 최종본에서 feedback.overall 로 옮겨갔다. "
        "프론트 전환 기간 동안만 feedback.overall 값을 그대로 복사해 채워준다.",
    )


class FeedbackResult(BaseModel):
    """AI v2 최종본의 최상위 feedback.

    v2 초안에서는 이 블록이 통째로 사라지고 종합 피드백이 content.overall 로 간다고
    되어 있었으나, 최종본에서는 feedback 이 남고 star_detail 만 제거됐다.
    (star_detail 의 내용은 star_score 각 항목의 comment 로 흡수)
    """

    star_overall: Optional[str] = Field(
        None, description="STAR 전체에 대한 종합 피드백. 비행동형 질문이면 null"
    )
    coherence_detail: Optional[str] = Field(None, description="두서없음 상세 설명")
    overall: Optional[str] = Field(None, description="종합 피드백 텍스트")


class SpeechAnalysisResponse(BaseModel):
    submission_id: uuid.UUID = Field(..., description="생성된 제출 ID")
    question_id: uuid.UUID = Field(..., description="대상 질문 ID")
    acoustic: AcousticResult
    content: ContentResult
    feedback: FeedbackResult = Field(default_factory=FeedbackResult)
