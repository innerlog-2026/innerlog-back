from fastapi import HTTPException


class InnerLogException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


class EmailAlreadyExistsError(InnerLogException):
    def __init__(self):
        super().__init__(409, "COMMON_409", "이미 사용 중인 이메일입니다.")


class InvalidCredentialsError(InnerLogException):
    def __init__(self):
        super().__init__(401, "AUTH_401", "이메일 또는 비밀번호가 올바르지 않습니다.")


class InvalidTokenError(InnerLogException):
    def __init__(self):
        super().__init__(401, "TOKEN_401", "유효하지 않은 토큰입니다.")


class TokenTypeError(InnerLogException):
    def __init__(self):
        super().__init__(401, "TOKEN_TYPE_401", "리프레시 토큰이 아닙니다.")


class ApplicationNotFoundError(InnerLogException):
    def __init__(self):
        super().__init__(404, "APPLICATION_404", "지원 현황을 찾을 수 없습니다.")


class QuestionNotFoundError(InnerLogException):
    def __init__(self):
        super().__init__(404, "QUESTION_404", "질문을 찾을 수 없습니다.")


class InvalidAudioFileError(InnerLogException):
    def __init__(self):
        super().__init__(400, "SPEECH_FILE_400", "지원하지 않는 음성 파일 형식입니다. (mp3, wav만 허용됩니다.)")


class AudioFileTooLargeError(InnerLogException):
    def __init__(self):
        super().__init__(413, "SPEECH_FILE_413", "음성 파일 용량이 너무 큽니다. (최대 100MB)")


class SpeechPracticeNotAllowedError(InnerLogException):
    def __init__(self):
        super().__init__(403, "SPEECH_403", "현재 전형 단계에서는 스피치 연습을 사용할 수 없습니다.")


class SpeechPracticeAlreadyExistsError(InnerLogException):
    def __init__(self):
        super().__init__(409, "SPEECH_409", "이미 스피치 연습이 생성된 지원 현황입니다.")


class ResumeTooShortError(InnerLogException):
    def __init__(self):
        super().__init__(
            400,
            "SPEECH_RESUME_400",
            "자기소개서 내용이 너무 짧습니다. 예상 질문을 생성하려면 최소 50자 이상 필요합니다.",
        )


class RetrospectNotAllowedError(InnerLogException):
    def __init__(self):
        super().__init__(403, "RETROSPECT_403", "현재 전형 단계에서는 면접 회고를 사용할 수 없습니다.")


class RetrospectAlreadyExistsError(InnerLogException):
    def __init__(self):
        super().__init__(409, "RETROSPECT_409", "이미 해당 면접 단계의 회고가 존재합니다.")


class SessionNotFoundError(InnerLogException):
    def __init__(self):
        super().__init__(404, "SESSION_404", "회고 세션을 찾을 수 없습니다.")


class RetrospectNotInProgressError(InnerLogException):
    def __init__(self):
        super().__init__(409, "RETROSPECT_PROGRESS_409", "이미 종료된 회고 세션입니다.")


class RetrospectNotDoneError(InnerLogException):
    def __init__(self):
        super().__init__(
            409,
            "RETROSPECT_DONE_409",
            "아직 회고가 완료되지 않았습니다. (대화가 DONE 단계에 도달해야 분석할 수 있습니다.)",
        )


class RetrospectAlreadyDoneError(InnerLogException):
    def __init__(self):
        super().__init__(
            409,
            "RETROSPECT_ALREADY_DONE_409",
            "회고 대화가 이미 종료되었습니다. 분석 결과를 요청해주세요.",
        )


class AIServerError(InnerLogException):
    def __init__(self):
        super().__init__(502, "AI_SERVER_ERROR", "AI 서버 호출에 실패했습니다.")
