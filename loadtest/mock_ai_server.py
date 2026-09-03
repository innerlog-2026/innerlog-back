"""
부하테스트용 Mock AI 서버

실제 AI 서버(LLM/RAG)는 응답이 느리고(30초~1분) 비용이 나며 매번 결과가 달라 before/after 비교가 불가능함. 
해당 Mock 서버는 "고정 지연"만 흉내내서 백엔드의 동시성 처리 능력(sync blocking → async)만 깨끗하게 측정하도록 함

- 지연 시간: 환경변수 AI_DELAY_SECONDS (기본 2.0초)
- 목 서버 자체는 async(asyncio.sleep)라 수천 개의 동시 요청을 병목 없이 흘려보낸다.
  → 병목은 오직 "테스트 대상 백엔드"에서만 발생한다.

실행:
    uvicorn loadtest.mock_ai_server:app --host 0.0.0.0 --port 9000
"""
import asyncio
import os

from fastapi import FastAPI

AI_DELAY_SECONDS = float(os.getenv("AI_DELAY_SECONDS", "2.0"))

app = FastAPI(title="Mock AI Server (loadtest)")

# generate_more_questions 의 dedup 과 맞물리도록 "고정" 질문 세트를 돌려준다.
# 시드 스크립트가 동일한 텍스트를 미리 넣어두면 steady-state 에서 added_count=0 (일정한 부하).
_FIXED_QUESTIONS = [
    {"question": "Spring Boot 프로젝트에서 가장 어려웠던 기술적 문제는 무엇이었나요?", "category": "기술"},
    {"question": "팀 프로젝트에서 갈등이 생겼을 때 어떻게 해결하셨나요?", "category": "인성"},
    {"question": "우리 회사에 지원한 이유가 무엇인가요?", "category": "공통"},
]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/question-extract")
async def question_extract(payload: dict):
    await asyncio.sleep(AI_DELAY_SECONDS)
    return {"questions": _FIXED_QUESTIONS}


@app.post("/speech-analyze")
async def speech_analyze(payload: dict):
    """AI API v2 응답 구조 (star_score 객체화 / coherence 객체 / content.overall)."""
    await asyncio.sleep(AI_DELAY_SECONDS)
    return {
        "acoustic": {
            "speed_wpm": 87.5,
            "speed_label": "적절",
            "filler_words": {"음": 2, "어": 1},
            "silence_count": 1,
            "duration_sec": 62,
            "word_count": 90,
        },
        "content": {
            "question_type": "행동형",
            "star_score": {
                "situation": {"present": True, "comment": "배경 상황이 구체적으로 설명됐습니다."},
                "task": {"present": False, "comment": "본인의 역할이 명확히 드러나지 않았습니다."},
                "action": {"present": True, "comment": "구체적인 행동이 잘 서술됐습니다."},
                "result": {"present": True, "comment": "결과가 명확히 제시됐습니다."},
            },
            "coherence": {"summary": "논리 흐름 양호", "detail": None},
            "keyword_repeat": {"프로젝트": 4},
            "negative_reframe": {"detected": False, "expressions": [], "feedback": None},
            "overall": "전반적으로 경험을 잘 구조화해서 설명했습니다.",
        },
    }


@app.post("/chat")
async def chat(payload: dict):
    """AI API v2: 첫 턴은 user_message="" 로 오면 AI가 먼저 인사를 생성한다."""
    await asyncio.sleep(AI_DELAY_SECONDS)
    state = dict(payload.get("state") or {})
    user_message = payload.get("user_message", "")
    is_opening = state.get("total_turn_count", 0) == 0 and user_message == ""

    ai_response = "(mock) 안녕하세요, 회고를 시작할게요." if is_opening else "(mock) 다음 질문입니다."

    history = list(state.get("history") or [])
    if user_message:  # v2 오프닝의 빈 문자열은 히스토리에 남기지 않는다
        history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_response})

    state["stage_turn_count"] = state.get("stage_turn_count", 0) + 1
    state["total_turn_count"] = state.get("total_turn_count", 0) + 1
    state["history"] = history
    return {"ai_response": ai_response, "updated_state": state}


@app.post("/summarize")
async def summarize(payload: dict):
    """AI API v2: 6개 분석 항목을 analysis 객체로 중첩하고 interview_type 을 쓴다."""
    await asyncio.sleep(AI_DELAY_SECONDS)
    return {
        "session_id": payload.get("session_id"),
        "company": "(mock) 카카오",
        "role": "(mock) 백엔드",
        "interview_type": "1차면접",
        "result": None,
        "analysis": {
            "summary": "(mock) 면접 회고 요약",
            "hypothesis": "(mock) 가설",
            "strengths": "(mock) 강점",
            "weaknesses": ["(mock) 약점1", "(mock) 약점2"],
            "gap_analysis": "(mock) 갭 분석",
            "actions": ["(mock) 액션1", "(mock) 액션2"],
        },
    }
