import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionStageEnum(str, enum.Enum):
    FACT = "FACT"
    INTERPRETATION = "INTERPRETATION"
    STRATEGY = "STRATEGY"
    DONE = "DONE"


class SessionStatusEnum(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class SessionTypeEnum(str, enum.Enum):
    FIRST = "1차면접"
    SECOND = "2차면접"
    FINAL = "최종면접"


class SenderEnum(str, enum.Enum):
    AI = "AI"
    USER = "USER"


class Session(Base):
    __tablename__ = "session"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.application_id"), nullable=False)
    stage: Mapped[SessionStageEnum] = mapped_column(SAEnum(SessionStageEnum), default=SessionStageEnum.FACT, nullable=False)
    status: Mapped[SessionStatusEnum] = mapped_column(SAEnum(SessionStatusEnum), default=SessionStatusEnum.IN_PROGRESS, nullable=False)
    type: Mapped[SessionTypeEnum] = mapped_column(SAEnum(SessionTypeEnum), nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="sessions")
    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="session")
    interview_analysis: Mapped[Optional["InterviewAnalysis"]] = relationship("InterviewAnalysis", back_populates="session", uselist=False)


class Chat(Base):
    __tablename__ = "chat"

    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session.session_id"), nullable=False)
    sender: Mapped[SenderEnum] = mapped_column(SAEnum(SenderEnum), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    session: Mapped["Session"] = relationship("Session", back_populates="chats")


class InterviewAnalysis(Base):
    __tablename__ = "interview_analysis"

    interview_analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session.session_id"), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hypothesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    gap_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actions: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="interview_analysis")
