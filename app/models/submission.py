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
    # AI v2: 채움말 -> 횟수 맵 (예: {"그": 1})
    filler_words: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    silence_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
            " AND jsonb_typeof(star_score->'situation'->'present') = 'boolean'"
            " AND jsonb_typeof(star_score->'task'->'present') = 'boolean'"
            " AND jsonb_typeof(star_score->'action'->'present') = 'boolean'"
            " AND jsonb_typeof(star_score->'result'->'present') = 'boolean'"
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
    # AI v2: {situation|task|action|result: {present: bool, comment: str}}
    #        행동형 질문이 아니면 전체가 NULL (STAR 미적용)
    star_score: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: {"summary": str, "detail": str|null}
    coherence: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: 키워드 -> 반복 횟수 맵
    keyword_repeat: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: {"detected": bool, "expressions": [...], "feedback": str|null}
    negative_reframe: Mapped[Optional[dict]] = mapped_column(JSONB(none_as_null=True), nullable=True)
    # AI v2: 종합 피드백 (v1 의 최상위 feedback.overall 이 content 로 이동)
    overall: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    speech_analysis: Mapped["SpeechAnalysis"] = relationship("SpeechAnalysis", back_populates="speech_content")
