from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, RefreshRequest
from app.services import auth as auth_service
from app.api.docs.auth import signup_docs, login_docs, refresh_docs

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201, **signup_docs)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    user = auth_service.signup(db, body)
    return TokenResponse(
        access_token=auth_service.create_access_token(str(user.user_id)),
        refresh_token=auth_service.create_refresh_token(str(user.user_id)),
    )


@router.post("/login", response_model=TokenResponse, **login_docs)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    access_token, refresh_token = auth_service.login(db, body)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse, **refresh_docs)
def refresh(body: RefreshRequest):
    access_token, refresh_token = auth_service.refresh_tokens(body.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
