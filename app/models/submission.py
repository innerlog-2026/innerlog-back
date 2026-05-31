import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
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
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    submission: Mapped["Submission"] = relationship("Submission", back_populates="speech_analysis")
    speech_acoustic: Mapped[Optional["SpeechAcoustic"]] = relationship("SpeechAcoustic", back_populates="speech_analysis", uselist=False)
    speech_content: Mapped[Optional["SpeechContent"]] = relationship("SpeechContent", back_populates="speech_analysis", uselist=False)


class SpeechAcoustic(Base):
    __tablename__ = "speech_acoustic"

    speech_acoustic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    speech_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("speech_analysis.speech_analysis_id"), nullable=False)
    speed_wpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speed_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filler_words: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    silence_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    speech_analysis: Mapped["SpeechAnalysis"] = relationship("SpeechAnalysis", back_populates="speech_acoustic")


class SpeechContent(Base):
    __tablename__ = "speech_content"

    speech_content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    speech_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("speech_analysis.speech_analysis_id"), nullable=False)
    star_situation: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    star_task: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    star_action: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    star_result: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    coherence: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    connectives_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    keyword_repeat: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    negative_reframe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    speech_analysis: Mapped["SpeechAnalysis"] = relationship("SpeechAnalysis", back_populates="speech_content")
