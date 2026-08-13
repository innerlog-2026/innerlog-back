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
    {"text": "Spring Boot 프로젝트에서 가장 어려웠던 기술적 문제는 무엇이었나요?", "category": "기술"},
    {"text": "팀 프로젝트에서 갈등이 생겼을 때 어떻게 해결하셨나요?", "category": "인성"},
    {"text": "우리 회사에 지원한 이유가 무엇인가요?", "category": "공통"},
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
    await asyncio.sleep(AI_DELAY_SECONDS)
    return {
        "acoustic": {
            "speed_wpm": 78.0,
            "speed_label": "평균보다 느린 편이에요",
            "filler_words": {"그": 1},
            "silence_count": 0,
            "duration_sec": 86.2,
            "word_count": 112,
        },
        "content": {
            "star_score": {"situation": True, "task": False, "action": True, "result": True},
            "coherence": "논리 흐름 양호",
            "keyword_repeat": {},
            "negative_reframe": {"detected": False, "expressions": [], "feedback": None},
        },
        "feedback": {
            "star_detail": {},
            "star_overall": "STAR 흐름 양호",
            "coherence_detail": "결론이 자연스럽게 마지막에 위치",
            "overall": "답변 구조가 좋습니다.",
        },
    }


@app.post("/chat")
async def chat(payload: dict):
    await asyncio.sleep(AI_DELAY_SECONDS)
    state = dict(payload.get("state") or {})
    state["stage_turn_count"] = state.get("stage_turn_count", 0) + 1
    state["total_turn_count"] = state.get("total_turn_count", 0) + 1
    history = list(state.get("history") or [])
    history.append({"role": "user", "content": payload.get("user_message", "")})
    history.append({"role": "assistant", "content": "(mock) 다음 질문입니다."})
    state["history"] = history
    return {"ai_response": "(mock) 다음 질문입니다.", "updated_state": state}


@app.post("/summarize")
async def summarize(payload: dict):
    await asyncio.sleep(AI_DELAY_SECONDS)
    return {
        "session_id": payload.get("session_id"),
        "summary": "(mock) 면접 회고 요약",
        "hypothesis": "(mock) 가설",
        "strengths": "(mock) 강점",
        "weaknesses": ["(mock) 약점1", "(mock) 약점2"],
        "gap_analysis": "(mock) 갭 분석",
        "actions": ["(mock) 액션1", "(mock) 액션2"],
    }
