from pydantic import BaseModel, EmailStr, Field
from app.models.user import PartEnum


class SignupRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일 주소", examples=["user@example.com"])
    password: str = Field(..., description="비밀번호 (8자 이상 권장)", examples=["password123!"])
    name: str = Field(..., description="이름", examples=["홍길동"])
    part: PartEnum = Field(..., description="관심 분야 (FRONT / BACK / AI / DATA)", examples=["BACK"])


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일 주소", examples=["user@example.com"])
    password: str = Field(..., description="비밀번호", examples=["password123!"])


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="액세스 토큰 (유효기간 30분)")
    refresh_token: str = Field(..., description="리프레시 토큰 (유효기간 7일)")
    token_type: str = Field(default="bearer", description="토큰 타입")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="재발급에 사용할 리프레시 토큰")


class ErrorResponse(BaseModel):
    code: str = Field(..., description="에러 코드", examples=["COMMON_409"])
    message: str = Field(..., description="에러 메시지", examples=["이미 사용 중인 이메일입니다."])
