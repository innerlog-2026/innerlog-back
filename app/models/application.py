import uuid
import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Text, Date, ForeignKey, UniqueConstraint, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LevelEnum(str, enum.Enum):
    HARD = "HARD"
    MEDIUM_HIGH = "MEDIUM_HIGH"
    MEDIUM_LOW = "MEDIUM_LOW"
    EASY = "EASY"


class ApplicationStatusEnum(str, enum.Enum):
    # 지원 현황 진행 상태 (진행중 / 완료 2가지)
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class StageEnum(str, enum.Enum):
    DOCUMENT = "서류전형"
    CODING_TEST = "코딩테스트"
    FIRST_INTERVIEW = "1차면접"
    SECOND_INTERVIEW = "2차면접"
    FINAL_INTERVIEW = "최종면접"


class StageStatusEnum(str, enum.Enum):
    # 전형 단계별 상태 (대기는 저장하지 않음 = 행이 없으면 대기)
    IN_PROGRESS = "진행중"
    PASS = "합격"
    FAIL = "탈락"


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
    status: Mapped[ApplicationStatusEnum] = mapped_column(SAEnum(ApplicationStatusEnum), default=ApplicationStatusEnum.IN_PROGRESS, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="applications")
    questions: Mapped[list["Question"]] = relationship("Question", back_populates="application")
    personal_statements: Mapped[list["PersonalStatement"]] = relationship("PersonalStatement", back_populates="application")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="application")
    stages: Mapped[list["ApplicationStage"]] = relationship("ApplicationStage", back_populates="application")


class Question(Base):
    __tablename__ = "question"

    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.application_id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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


class ApplicationStage(Base):
    __tablename__ = "application_stage"
    __table_args__ = (
        # 한 지원의 같은 전형 단계는 1행만 (upsert 기준)
        UniqueConstraint("application_id", "stage", name="uq_application_stage_app_stage"),
    )

    application_stage_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.application_id"), nullable=False)
    stage: Mapped[StageEnum] = mapped_column(SAEnum(StageEnum), nullable=False)
    status: Mapped[StageStatusEnum] = mapped_column(SAEnum(StageStatusEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="stages")
