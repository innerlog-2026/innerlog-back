from app.core.exceptions import InnerLogException
from app.schemas.auth import ErrorResponse


def error_response(description: str, *exceptions: type[InnerLogException]) -> dict:
    # 예외 클래스의 code/message로 OpenAPI 에러 응답 예시를 생성
    details = [exc().detail for exc in exceptions]
    if len(details) == 1:
        content = {"application/json": {"example": details[0]}}
    else:
        content = {
            "application/json": {
                "examples": {
                    detail["code"]: {"summary": detail["message"], "value": detail}
                    for detail in details
                }
            }
        }
    return {
        "description": description,
        "model": ErrorResponse,
        "content": content,
    }
