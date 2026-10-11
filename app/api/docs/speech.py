from app.api.docs.responses import error_response
from app.core.exceptions import (
    AIServerError,
    AIServerTimeoutError,
    AIServerUnreachableError,
    ApplicationNotFoundError,
    AudioFileTooLargeError,
    InvalidAudioFileError,
    InvalidTokenError,
    QuestionNotFoundError,
    ResumeTooShortError,
    SpeechPracticeAlreadyExistsError,
    SpeechPracticeNotAllowedError,
)

_unauthorized_response = error_response("인증 실패", InvalidTokenError)
_application_not_found_response = error_response("지원 현황 없음", ApplicationNotFoundError)
_speech_not_allowed_response = error_response(
    "스피치 연습을 사용할 수 없는 전형 단계", SpeechPracticeNotAllowedError
)
_ai_server_error_response = error_response("AI 서버 호출 실패", AIServerError)
_ai_server_unreachable_response = error_response(
    "AI 서버 연결 실패 (서버 다운 / 네트워크 경로 단절)", AIServerUnreachableError
)
_ai_server_timeout_response = error_response(
    "AI 서버 응답 지연 (제한 시간 초과)", AIServerTimeoutError
)
_speech_already_exists_response = error_response(
    "이미 스피치 연습이 생성됨", SpeechPracticeAlreadyExistsError
)
_question_not_found_response = error_response("질문 없음", QuestionNotFoundError)
_resume_too_short_response = error_response("자기소개서 길이 부족", ResumeTooShortError)
_invalid_audio_response = error_response("잘못된 음성 파일 형식", InvalidAudioFileError)
_audio_too_large_response = error_response("음성 파일 용량 초과", AudioFileTooLargeError)

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
        400: _resume_too_short_response,
        401: _unauthorized_response,
        403: _speech_not_allowed_response,
        404: _application_not_found_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)

create_speech_practice_docs = dict(
    summary="스피치 연습 등록 (예상 질문 생성, 최초 1회)",
    description="예상 질문 생성 API. 지원 현황당 최초 1회만 호출할 수 있습니다.",
    responses={
        201: {"description": "예상 질문 생성 성공"},
        400: _resume_too_short_response,
        401: _unauthorized_response,
        403: _speech_not_allowed_response,
        404: _application_not_found_response,
        409: _speech_already_exists_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)

# AI v2 최종 명세(`/speech-analyze star_score 포맷 변경`)의 두 예시를 그대로 실는다.
# 프론트가 행동형/비행동형 분기를 문서만 보고 구현할 수 있도록 둘 다 노출한다.
_speed_baseline_example = {
    "mean": 90.14,
    "p5": 65.3,
    "p33": 83.16,
    "p67": 96.6,
    "p95": 116.04,
    "source": "AI Hub 채용면접 데이터 (ICT 직군)",
    "sample_count": 6571,
}
_length_baseline_example = {
    "mean": 89.38,
    "p5": 45.86,
    "p33": 84.04,
    "p67": 104.68,
    "p95": 119.68,
    "unit": "sec",
    "source": "AI Hub 채용면접 데이터 (ICT 직군)",
    "sample_count": 5844,
}

_analyze_speech_success_response = {
    "description": "스피치 분석 성공",
    "content": {
        "application/json": {
            "examples": {
                "behavioral": {
                    "summary": "행동형 질문 (STAR 적용)",
                    "value": {
                        "submission_id": "3f1c2b9e-0a1d-4c7b-9a2e-8d5f6b7c1a23",
                        "question_id": "9b8a7c6d-5e4f-4321-8765-1a2b3c4d5e6f",
                        "acoustic": {
                            "speed_wpm": 87.5,
                            "speed_label": "평균(90.14어절/분)과 비슷한 수준이에요",
                            "speed_baseline": _speed_baseline_example,
                            "filler_words": {"음": 2, "어": 1},
                            "silence_count": 1,
                            "duration_sec": 62.0,
                            "word_count": 90,
                            "length_label": "평균(89.38초)보다 짧은 편이에요",
                            "length_baseline": _length_baseline_example,
                        },
                        "content": {
                            "question_type": "행동형",
                            "star_score": {
                                "situation": {"present": True, "comment": "상황 설명이 잘 드러났습니다."},
                                "task": {"present": False, "comment": "본인의 역할이 명확하지 않았습니다."},
                                "action": {"present": True, "comment": "구체적인 행동이 잘 서술되었습니다."},
                                "result": {"present": True, "comment": "결과가 명확하게 제시되었습니다."},
                            },
                            "coherence": {"summary": "논리 흐름 양호", "detail": None},
                            "keyword_repeat": {},
                            "negative_reframe": {"detected": False, "expressions": [], "feedback": None},
                            "overall": "경험을 구조적으로 잘 서술하셨습니다.",
                        },
                        "feedback": {
                            "star_overall": "상황과 행동은 잘 설명했지만, 본인의 역할과 결과를 더 구체적으로 말해보세요.",
                            "coherence_detail": None,
                            "overall": "경험을 구조적으로 잘 서술하셨습니다.",
                        },
                    },
                },
                "non_behavioral": {
                    "summary": "비행동형 질문 (의견형 — STAR 미적용)",
                    "value": {
                        "submission_id": "3f1c2b9e-0a1d-4c7b-9a2e-8d5f6b7c1a23",
                        "question_id": "9b8a7c6d-5e4f-4321-8765-1a2b3c4d5e6f",
                        "acoustic": {
                            "speed_wpm": 79.5,
                            "speed_label": "평균(90.14어절/분)보다 느린 편이에요",
                            "speed_baseline": _speed_baseline_example,
                            "filler_words": {},
                            "silence_count": 0,
                            "duration_sec": 40.0,
                            "word_count": 53,
                            "length_label": "평균(89.38초)보다 짧은 편이에요",
                            "length_baseline": _length_baseline_example,
                        },
                        "content": {
                            "question_type": "의견형",
                            "star_score": {
                                "situation": {"present": None, "comment": None},
                                "task": {"present": None, "comment": None},
                                "action": {"present": None, "comment": None},
                                "result": {"present": None, "comment": None},
                            },
                            "coherence": {"summary": "논리 흐름 양호", "detail": None},
                            "keyword_repeat": {},
                            "negative_reframe": {"detected": False, "expressions": [], "feedback": None},
                            "overall": "주장이 명확하고 근거를 잘 들어 설명하셨습니다.",
                        },
                        "feedback": {
                            "star_overall": None,
                            "coherence_detail": None,
                            "overall": "주장이 명확하고 근거를 잘 들어 설명하셨습니다.",
                        },
                    },
                },
            }
        }
    },
}

analyze_speech_docs = dict(
    summary="스피치 분석 (음성 파일 업로드 → AI 분석)",
    description=(
        "질문에 대한 답변 음성 파일(mp3/wav, 최대 100MB)을 multipart/form-data로 업로드하면 "
        "공유 볼륨에 저장한 뒤 AI 서버에 스피치 분석을 요청하고, 분석 결과를 반환합니다. "
        "제출 및 분석 결과는 DB에 저장되어 재조회할 수 있습니다."
    ),
    responses={
        201: _analyze_speech_success_response,
        400: _invalid_audio_response,
        401: _unauthorized_response,
        404: _question_not_found_response,
        413: _audio_too_large_response,
        502: _ai_server_error_response,
        503: _ai_server_unreachable_response,
        504: _ai_server_timeout_response,
    },
)
