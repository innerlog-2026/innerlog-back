import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, CheckConstraint, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InputTypeEnum(str, enum.Enum):
    RECORDING = "RECORDING"
    UPLOAD = "UPLOAD"


class Submission(Base):
    __tablename__ = "submission"

    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("question.question_id"), nullable=False)
    input_type: Mapped[InputTypeEnum] = mapped_column(SAEnum(InputTypeEnum), nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="submissions")
    speech_analysis: Mapped[Optional["SpeechAnalysis"]] = relationship("SpeechAnalysis", back_populates="submission", uselist=False)


class SpeechAnalysis(Base):
    __tablename__ = "speech_analysis"

    speech_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submission.submission_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    submission: Mapped["Submission"] = relationship("Submission", back_populates="speech_analysis")
    speech_acoustic: Mapped[Optional["SpeechAcoustic"]] = relationship("SpeechAcoustic", back_populates="speech_analysis", uselist=False)
    speech_content: Mapped[Optional["SpeechContent"]] = relationship("SpeechContent", back_populates="speech_analysis", uselist=False)


class SpeechAcoustic(Base):
    __tablename__ = "speech_acoustic"

    speech_acoustic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    speech_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("speech_analysis.speech_analysis_id"), nullable=False)
    speed_wpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # 말 속도 기준값 {mean, p5, p33, p67, p95, source, sample_count}
    speed_baseline: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: 채움말 -> 횟수 맵 (예: {"그": 1})
    filler_words: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    silence_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    length_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # 답변 시간 기준값 {mean, p5, p33, p67, p95, unit, source, sample_count}
    length_baseline: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)

    speech_analysis: Mapped["SpeechAnalysis"] = relationship("SpeechAnalysis", back_populates="speech_acoustic")


class SpeechContent(Base):
    __tablename__ = "speech_content"
    # JSONB 를 쓰되 "앱이 의존하는 불변식"만 DB 레벨에서 강제
    # 미지의 키(예: 명세 추가 필드)는 통과시켜 JSONB 의 유연성을 유지
    __table_args__ = (
        CheckConstraint(
            "star_score IS NULL OR ("
            " jsonb_typeof(star_score) = 'object'"
            " AND jsonb_exists_all(star_score, ARRAY['situation','task','action','result'])"
            # 각 항목은 (1) 키 자체가 JSON null 이거나
            #          (2) present 키를 가진 객체이고 present 가 boolean 또는 null
            # 셋 중 하나여야 한다. 비행동형 질문에서 present 가 null 로 오므로
            # boolean 만 허용하면 의견형 답변 저장이 제약 위반으로 실패한다.
            " AND COALESCE(jsonb_typeof(star_score->'situation') = 'null'"
            "          OR (jsonb_typeof(star_score->'situation') = 'object'"
            "              AND jsonb_typeof(star_score->'situation'->'present') IN ('boolean','null')), false)"
            " AND COALESCE(jsonb_typeof(star_score->'task') = 'null'"
            "          OR (jsonb_typeof(star_score->'task') = 'object'"
            "              AND jsonb_typeof(star_score->'task'->'present') IN ('boolean','null')), false)"
            " AND COALESCE(jsonb_typeof(star_score->'action') = 'null'"
            "          OR (jsonb_typeof(star_score->'action') = 'object'"
            "              AND jsonb_typeof(star_score->'action'->'present') IN ('boolean','null')), false)"
            " AND COALESCE(jsonb_typeof(star_score->'result') = 'null'"
            "          OR (jsonb_typeof(star_score->'result') = 'object'"
            "              AND jsonb_typeof(star_score->'result'->'present') IN ('boolean','null')), false)"
            ")",
            name="ck_speech_content_star_score",
        ),
        CheckConstraint(
            "coherence IS NULL OR ("
            " jsonb_typeof(coherence) = 'object'"
            " AND jsonb_exists(coherence, 'summary')"
            ")",
            name="ck_speech_content_coherence",
        ),
    )

    speech_content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    speech_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("speech_analysis.speech_analysis_id"), nullable=False)
    # AI v2: 질문 유형 (행동형 / 의견형 / 기술형 / 가정형)
    question_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # AI v2 최종: {situation|task|action|result: {present: bool|null, comment: str|null}}
    #             비행동형 질문이면 4개 항목의 present/comment 가 모두 null
    star_score: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: {"summary": str, "detail": str|null}
    coherence: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: 키워드 -> 반복 횟수 맵
    keyword_repeat: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: {"detected": bool, "expressions": [...], "feedback": str|null}
    negative_reframe: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2 최종: 종합 피드백. 최상위 feedback.overall 에서 가져온다
    # (v2 초안은 content.overall 로 옮긴다고 했으나 최종본에서 feedback 이 유지됐다)
    overall: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # AI v2 최종: 최상위 feedback.star_overall — STAR 전체 종합 피드백. 비행동형이면 null
    star_overall: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # AI v2 최종: 최상위 feedback.coherence_detail — 두서없음 상세 설명
    coherence_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    speech_analysis: Mapped["SpeechAnalysis"] = relationship("SpeechAnalysis", back_populates="speech_content")
