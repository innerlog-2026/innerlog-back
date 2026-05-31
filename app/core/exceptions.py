from fastapi import HTTPException


class InnerLogException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


class EmailAlreadyExistsError(InnerLogException):
    def __init__(self):
        super().__init__(409, "EMAIL_ALREADY_EXISTS", "이미 사용 중인 이메일입니다.")


class InvalidCredentialsError(InnerLogException):
    def __init__(self):
        super().__init__(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")


class InvalidTokenError(InnerLogException):
    def __init__(self):
        super().__init__(401, "INVALID_TOKEN", "유효하지 않은 토큰입니다.")


class TokenTypeError(InnerLogException):
    def __init__(self):
        super().__init__(401, "INVALID_TOKEN_TYPE", "리프레시 토큰이 아닙니다.")
