from app.schemas.auth import ErrorResponse

create_application_docs = dict(
    summary="지원 현황 생성",
    description="지원 현황 생성 API",
    responses={
        201: {"description": "지원 현황 생성 성공"},
        401: {
            "description": "인증 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"code": "INVALID_TOKEN", "message": "유효하지 않은 토큰입니다."}
                }
            },
        },
    },
)
