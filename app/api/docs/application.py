from app.api.docs.responses import error_response
from app.core.exceptions import ApplicationNotFoundError, InvalidTokenError

_unauthorized_response = error_response("인증 실패", InvalidTokenError)
_not_found_response = error_response("지원 현황 없음", ApplicationNotFoundError)

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

update_stage_result_docs = dict(
    summary="진행 결과 수정",
    description="지원 현황의 특정 전형 단계 상태(진행중/합격/탈락)를 설정한다. "
    "(지원, 단계) 단위로 upsert하며 현재 진행 단계 포인터도 함께 갱신한다. "
    "'대기'는 저장하지 않는다(행이 없으면 대기).",
    responses={
        200: {"description": "진행 결과 수정 성공"},
        401: _unauthorized_response,
        404: _not_found_response,
    },
)

get_application_detail_docs = dict(
    summary="지원 현황 상세 조회",
    description="지원 현황 상세 + 전형 진행 단계 타임라인을 조회한다. "
    "타임라인은 고정 파이프라인 전체를 순서대로 반환하며, 각 단계 상태는 대기/진행중/합격/탈락이다 "
    "(도달하지 않은 단계는 '대기'; 대기는 저장하지 않고 응답에서 파생). "
    "현재 전형 단계의 상태와 1·2차 면접 회고 완료 여부(회고 세션 COMPLETED)도 포함한다.",
    responses={
        200: {"description": "지원 현황 상세 조회 성공"},
        401: _unauthorized_response,
        404: _not_found_response,
    },
)
