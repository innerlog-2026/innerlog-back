"""
부하테스트 비교용 동기(sync) 백엔드 앱.

app.main.app 에서 POST /speech-practices/{application_id}/questions 라우트만
리팩토링 이전 동작(동기 def 라우트 → 스레드풀 실행, AI 호출 내내 DB 커넥션 점유)으로 교체함.
나머지 라우트·미들웨어·설정은 app.main 과 동일함.

실행:
    uvicorn loadtest.sync_app:app --port 8000
"""
import uuid

from fastapi import Depends
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.speech import generate_speech_practice_questions_docs
from app.api.speech import _build_generate_response
from app.core.database import get_db
from app.main import app
from app.models.user import User
from app.schemas.speech import SpeechPracticeQuestionGenerateResponse
from app.services import speech as speech_service

_PATH = "/speech-practices/{application_id}/questions"

# async 버전 라우트를 제거하고 같은 경로에 동기 라우트를 등록함.
app.router.routes = [
    route
    for route in app.router.routes
    if not (isinstance(route, APIRoute) and route.path == _PATH and "POST" in route.methods)
]


@app.post(
    _PATH,
    response_model=SpeechPracticeQuestionGenerateResponse,
    status_code=201,
    **generate_speech_practice_questions_docs,
)
def generate_speech_practice_questions_sync(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    added = speech_service.generate_more_questions(db, current_user.user_id, application_id)
    return _build_generate_response(application_id, added)
