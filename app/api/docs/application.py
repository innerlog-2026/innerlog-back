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

list_applications_docs = dict(
    summary="지원 현황 목록 조회",
    description="로그인한 사용자의 지원 현황을 최신순으로 페이지네이션(한 페이지당 5개) 조회한다. "
    "각 항목은 기업명·전형단계·현황과 이동용 지원 현황 ID를 담는다.",
    responses={
        200: {"description": "지원 현황 목록 조회 성공"},
        401: _unauthorized_response,
    },
)
