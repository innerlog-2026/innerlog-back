import uuid
import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Text, Date, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LevelEnum(str, enum.Enum):
    HARD = "HARD"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    MEDIUM_LOW = "MEDIUM_LOW"
    EASY = "EASY"


class ApplicationStatusEnum(str, enum.Enum):
    PREPARING = "PREPARING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class StageEnum(str, enum.Enum):
    DOCUMENT = "서류전형"
    CODING_TEST = "코딩테스트"
    FIRST_INTERVIEW = "1차면접"
    SECOND_INTERVIEW = "2차면접"
    FINAL_INTERVIEW = "최종면접"


class Application(Base):
    __tablename__ = "application"

    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[Optional[StageEnum]] = mapped_column(SAEnum(StageEnum), nullable=True)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    level: Mapped[Optional[LevelEnum]] = mapped_column(SAEnum(LevelEnum), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatusEnum] = mapped_column(SAEnum(ApplicationStatusEnum), default=ApplicationStatusEnum.PREPARING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="applications")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="application")
    personal_statements: Mapped[list["PersonalStatement"]] = relationship("PersonalStatement", back_populates="application")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="application")


class Question(Base):
    __tablename__ = "question"

    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.application_id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="questions")
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="question")


class PersonalStatement(Base):
    __tablename__ = "personal_statement"

    personal_statement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.application_id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="personal_statements")
