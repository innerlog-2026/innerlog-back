from app.api.docs.responses import error_response
from app.core.exceptions import InvalidTokenError

_unauthorized_response = error_response("인증 실패", InvalidTokenError)

create_application_docs = dict(
    summary="지원 현황 생성",
    description="지원 현황 생성 API",
    responses={
        201: {"description": "지원 현황 생성 성공"},
        401: _unauthorized_response,
    },
)
