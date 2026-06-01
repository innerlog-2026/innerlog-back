from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.speech import create_speech_practice_docs
from app.core.database import get_db
from app.models.user import User
from app.schemas.speech import (
    QuestionItem,
    SpeechPracticeCreateReq,
    SpeechPracticeCreateResponse,
)
from app.services import speech as speech_service

router = APIRouter(prefix="/speech-practices", tags=["Speech Practice"])


@router.post("", response_model=SpeechPracticeCreateResponse, status_code=201, **create_speech_practice_docs)
def create_speech_practice(
    body: SpeechPracticeCreateReq,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application_id, questions = speech_service.create_speech_practice(db, current_user.user_id, body)
    return SpeechPracticeCreateResponse(
        application_id=application_id,
        questions=[QuestionItem.model_validate(question) for question in questions],
    )
