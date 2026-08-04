from app.api.docs.responses import error_response
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenTypeError,
)

_email_already_exists_response = error_response("이메일 중복", EmailAlreadyExistsError)
_invalid_credentials_response = error_response("인증 실패", InvalidCredentialsError)
_refresh_token_invalid_response = error_response(
    "토큰 검증 실패", InvalidTokenError, TokenTypeError
)

signup_docs = dict(
    summary="회원가입",
    description="회원가입 API",
    responses={
        201: {"description": "회원가입 성공 — 토큰 발급"},
        409: _email_already_exists_response,
    },
)

login_docs = dict(
    summary="로그인",
    description="로그인 API",
    responses={
        200: {"description": "로그인 성공 — 토큰 발급"},
        401: _invalid_credentials_response,
    },
)

refresh_docs = dict(
    summary="토큰 재발급",
    description="유효한 리프레시 토큰을 사용하여 새로운 액세스 토큰과 리프레시 토큰을 발급",
    responses={
        200: {"description": "토큰 재발급 성공"},
        401: _refresh_token_invalid_response,
    },
)
