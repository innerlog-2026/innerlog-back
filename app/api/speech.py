import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.docs.speech import (
    analyze_speech_docs,
    create_speech_practice_docs,
    generate_speech_practice_questions_docs,
    list_speech_practice_questions_docs,
)
from app.core.database import get_db
from app.models.submission import InputTypeEnum
from app.models.user import User
from app.schemas.speech import (
    QuestionItem,
    QuestionProgressItem,
    SpeechAnalysisResponse,
    SpeechPracticeCreateReq,
    SpeechPracticeCreateResponse,
    SpeechPracticeQuestionGenerateResponse,
    SpeechPracticeQuestionListResponse,
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


@router.get(
    "/{application_id}/questions",
    response_model=SpeechPracticeQuestionListResponse,
    **list_speech_practice_questions_docs,
)
def list_speech_practice_questions(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    questions, practiced_ids = speech_service.list_questions(db, current_user.user_id, application_id)
    items = [
        QuestionProgressItem(
            question_id=question.question_id,
            question=question.question,
            category=question.category,
            sequence=question.sequence,
            is_practiced=question.question_id in practiced_ids,
        )
        for question in questions
    ]
    return SpeechPracticeQuestionListResponse(
        application_id=application_id,
        total_count=len(items),
        practiced_count=sum(1 for item in items if item.is_practiced),
        questions=items,
    )


@router.post(
    "/{application_id}/questions",
    response_model=SpeechPracticeQuestionGenerateResponse,
    status_code=201,
    **generate_speech_practice_questions_docs,
)
def generate_speech_practice_questions(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    added = speech_service.generate_more_questions(db, current_user.user_id, application_id)
    return SpeechPracticeQuestionGenerateResponse(
        application_id=application_id,
        added_count=len(added),
        questions=[QuestionItem.model_validate(question) for question in added],
    )


@router.post(
    "/questions/{question_id}/submissions",
    response_model=SpeechAnalysisResponse,
    status_code=201,
    **analyze_speech_docs,
)
def analyze_speech_submission(
    question_id: uuid.UUID,
    file: UploadFile = File(..., description="답변 음성 파일 (mp3/wav, 최대 100MB)"),
    input_type: InputTypeEnum = Form(InputTypeEnum.UPLOAD, description="입력 방식 (RECORDING: 녹음 / UPLOAD: 파일 업로드)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    submission, result = speech_service.analyze_speech(
        db, current_user.user_id, question_id, file, input_type
    )
    return SpeechAnalysisResponse(
        submission_id=submission.submission_id,
        question_id=question_id,
        acoustic=result.get("acoustic") or {},
        content=result.get("content") or {},
        feedback=result.get("feedback") or {},
    )
