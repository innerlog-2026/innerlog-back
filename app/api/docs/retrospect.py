from app.api.docs.responses import error_response
from app.core.exceptions import (
    AIServerError,
    AIServerTimeoutError,
    AIServerUnreachableError,
    ApplicationNotFoundError,
    InvalidTokenError,
    RetrospectAlreadyDoneError,
    RetrospectAlreadyExistsError,
    RetrospectNotAllowedError,
    RetrospectNotDoneError,
    RetrospectNotInProgressError,
    SessionNotFoundError,
)

_unauthorized_response = error_response("인증 실패", InvalidTokenError)
_application_not_found_response = error_response("지원 현황 없음", ApplicationNotFoundError)
_session_not_found_response = error_response("회고 세션 없음", SessionNotFoundError)
_retrospect_not_allowed_response = error_response(
    "면접 회고를 사용할 수 없는 전형 단계/상태", RetrospectNotAllowedError
)
_retrospect_already_exists_response = error_response(
    "이미 해당 면접 단계의 회고가 존재함", RetrospectAlreadyExistsError
)
_retrospect_not_in_progress_response = error_response(
    "이미 종료된 회고 세션", RetrospectNotInProgressError
)
_chat_conflict_response = error_response(
    "채팅할 수 없는 상태 (종료된 세션 / 이미 DONE 도달)",
    RetrospectNotInProgressError,
    RetrospectAlreadyDoneError,
)
_retrospect_not_done_response = error_response(
    "회고 대화가 아직 DONE 단계가 아님", RetrospectNotDoneError
)
_ai_server_error_response = error_response("AI 서버 호출 실패", AIServerError)
_ai_server_unreachable_response = error_response(
    "AI 서버 연결 실패 (서버 다운 / 네트워크 경로 단절)", AIServerUnreachableError
)
_ai_server_timeout_response = error_response(
    "AI 서버 응답 지연 (제한 시간 초과)", AIServerTimeoutError
)

start_retrospect_docs = dict(
    summary="면접 회고 시작",
    description=(
        "지원 현황이 1차면접/2차면접/최종면접 단계의 COMPLETED 상태일 때 면접 회고를 시작합니다. "
        "면접 난이도(필수)와 메모(선택)를 입력하면 회고 세션을 생성하고, AI 서버 POST /chat을 호출해 "
        "첫 인사 메시지를 받아 반환합니다. 면접 단계당 1회만 시작할 수 있습니다."
    ),
    responses={
        201: {"description": "회고 시작 성공 (첫 AI 인사 포함)"},
        401: _unauthorized_response,
        403: _retrospect_not_allowed_response,
        404: _application_not_found_response,
        409: _retrospect_already_exists_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)

chat_retrospect_docs = dict(
    summary="회고 대화 한 턴",
    description=(
        "사용자 답변을 보내고 AI 서버 POST /chat을 호출해 다음 응답을 받습니다. "
        "응답의 stage가 DONE이 되면(is_done=true) 대화가 종료되며, 더 이상 채팅할 수 없습니다. "
        "이후에는 summarize 엔드포인트로 분석을 생성하세요. (DONE 이후 이 API 호출 시 409)"
    ),
    responses={
        200: {"description": "대화 응답 성공"},
        401: _unauthorized_response,
        404: _session_not_found_response,
        409: _chat_conflict_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)

summarize_retrospect_docs = dict(
    summary="회고 분석 결과 생성/조회",
    description=(
        "대화가 DONE 단계에 도달한 뒤 AI 서버 POST /summarize를 호출해 회고 분석 결과를 생성합니다. "
        "이미 생성된 경우 AI를 다시 호출하지 않고 저장된 결과를 그대로 반환합니다(멱등). "
        "생성 시 세션 상태가 COMPLETED로 전환됩니다."
    ),
    responses={
        200: {"description": "분석 결과 생성/조회 성공"},
        401: _unauthorized_response,
        404: _session_not_found_response,
        409: _retrospect_not_done_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)

get_retrospect_docs = dict(
    summary="회고 세션 상세 조회",
    description="세션 메타 정보 + 전체 대화 이력 + (있으면) 분석 결과를 조회합니다. 진행 중인 회고 이어가기에도 사용합니다.",
    responses={
        200: {"description": "세션 상세 조회 성공"},
        401: _unauthorized_response,
        404: _session_not_found_response,
    },
)

list_retrospects_docs = dict(
    summary="지원현황별 회고 세션 목록 조회",
    description="특정 지원 현황에 속한 회고 세션 목록을 조회합니다. (대화 이력/분석은 제외 — 상세는 세션 상세 조회 사용)",
    responses={
        200: {"description": "회고 세션 목록 조회 성공"},
        401: _unauthorized_response,
        404: _application_not_found_response,
    },
)
