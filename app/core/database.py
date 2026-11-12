from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def violated_constraint(exc: IntegrityError) -> Optional[str]:
    """IntegrityError 에서 위반된 제약조건 이름을 꺼냄."""
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None)
