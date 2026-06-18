from app.api.docs.responses import error_response
from app.core.exceptions import (
    AIServerError,
    ApplicationNotFoundError,
    InvalidTokenError,
    SpeechPracticeAlreadyExistsError,
    SpeechPracticeNotAllowedError,
)

_unauthorized_response = error_response("인증 실패", InvalidTokenError)
_application_not_found_response = error_response("지원 현황 없음", ApplicationNotFoundError)
_speech_not_allowed_response = error_response(
    "스피치 연습을 사용할 수 없는 전형 단계", SpeechPracticeNotAllowedError
)
_ai_server_error_response = error_response("AI 서버 호출 실패", AIServerError)
_speech_already_exists_response = error_response(
    "이미 스피치 연습이 생성됨", SpeechPracticeAlreadyExistsError
)

list_speech_practice_questions_docs = dict(
    summary="면접 예상 질문 리스트 조회",
    description="저장된 예상 질문 목록과 질문별 연습 진척도를 조회합니다. (AI 호출 X)",
    responses={
        200: {"description": "질문 리스트 조회 성공"},
        401: _unauthorized_response,
        404: _application_not_found_response,
    },
)

generate_speech_practice_questions_docs = dict(
    summary="면접 예상 질문 추가 생성",
    description=(
        "AI를 다시 호출해 예상 질문을 추가로 생성합니다. 기존 질문과 텍스트가 "
        "완전히 동일한 항목은 제외하고 이어서 추가됩니다."
    ),
    responses={
        201: {"description": "예상 질문 추가 생성 성공"},
        401: _unauthorized_response,
        403: _speech_not_allowed_response,
        404: _application_not_found_response,
        502: _ai_server_error_response,
    },
)

create_speech_practice_docs = dict(
    summary="스피치 연습 등록 (예상 질문 생성, 최초 1회)",
    description="예상 질문 생성 API. 지원 현황당 최초 1회만 호출할 수 있습니다.",
    responses={
        201: {"description": "예상 질문 생성 성공"},
        401: _unauthorized_response,
        403: _speech_not_allowed_response,
        404: _application_not_found_response,
        409: _speech_already_exists_response,
        502: _ai_server_error_response,
    },
)
