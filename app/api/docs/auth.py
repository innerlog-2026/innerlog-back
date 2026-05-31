from app.schemas.auth import ErrorResponse

signup_docs = dict(
    summary="회원가입",
    description="회원가입 API",
    responses={
        201: {"description": "회원가입 성공 — 토큰 발급"},
        409: {
            "description": "이메일 중복",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"code": "EMAIL_ALREADY_EXISTS", "message": "이미 사용 중인 이메일입니다."}
                }
            },
        },
    },
)

login_docs = dict(
    summary="로그인",
    description="로그인 API",
    responses={
        200: {"description": "로그인 성공 — 토큰 발급"},
        401: {
            "description": "인증 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"code": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다."}
                }
            },
        },
    },
)

refresh_docs = dict(
    summary="토큰 재발급",
    description="유효한 리프레시 토큰을 사용하여 새로운 액세스 토큰과 리프레시 토큰을 발급",
    responses={
        200: {"description": "토큰 재발급 성공"},
        401: {
            "description": "토큰 검증 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "유효하지 않은 토큰",
                            "value": {"code": "INVALID_TOKEN", "message": "유효하지 않은 토큰입니다."},
                        },
                        "wrong_type": {
                            "summary": "토큰 타입 오류",
                            "value": {"code": "INVALID_TOKEN_TYPE", "message": "리프레시 토큰이 아닙니다."},
                        },
                    }
                }
            },
        },
    },
)
