from app.schemas.auth import ErrorResponse

create_speech_practice_docs = dict(
    summary="스피치 연습 등록 (예상 질문 생성)",
    description="예상 질문 생성 API",
    responses={
        201: {"description": "예상 질문 생성 성공"},
        401: {
            "description": "인증 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"code": "TOKEN_401", "message": "유효하지 않은 토큰입니다."}
                }
            },
        },
        403: {
            "description": "스피치 연습을 사용할 수 없는 전형 단계",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "code": "SPEECH_403",
                        "message": "현재 전형 단계에서는 스피치 연습을 사용할 수 없습니다.",
                    }
                }
            },
        },
        404: {
            "description": "지원 현황 없음",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "code": "APPLICATION_404",
                        "message": "지원 현황을 찾을 수 없습니다.",
                    }
                }
            },
        },
        502: {
            "description": "AI 서버 호출 실패",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"code": "AI_SERVER_ERROR", "message": "AI 서버 호출에 실패했습니다."}
                }
            },
        },
    },
)
