import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PartEnum(str, enum.Enum):
    FRONT = "FRONT"
    BACK = "BACK"
    AI = "AI"
    DATA = "DATA"


class User(Base):
    __tablename__ = "user"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    part: Mapped[PartEnum] = mapped_column(SAEnum(PartEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    dashboard: Mapped[Optional["Dashboard"]] = relationship("Dashboard", back_populates="user", uselist=False)
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="user")


class Dashboard(Base):
    __tablename__ = "dashboard"

    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.user_id"), nullable=False)
    apply_cnt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_cnt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    keyword: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="dashboard")
