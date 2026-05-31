from datetime import datetime, timedelta

import bcrypt
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import EmailAlreadyExistsError, InvalidCredentialsError, InvalidTokenError, TokenTypeError
from app.models.user import User
from app.schemas.auth import SignupRequest, LoginRequest

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "type": "access", "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": user_id, "type": "refresh", "exp": expire}, settings.SECRET_KEY, algorithm=ALGORITHM)


def refresh_tokens(refresh_token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise InvalidTokenError()

    if payload.get("type") != "refresh":
        raise TokenTypeError()

    user_id = payload["sub"]
    return create_access_token(user_id), create_refresh_token(user_id)


def signup(db: Session, body: SignupRequest) -> User:
    if db.query(User).filter(User.email == body.email).first():
        raise EmailAlreadyExistsError()

    user = User(
        email=body.email,
        password=hash_password(body.password),
        name=body.name,
        part=body.part,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, body: LoginRequest) -> tuple[str, str]:
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise InvalidCredentialsError()

    return create_access_token(str(user.user_id)), create_refresh_token(str(user.user_id))
