# AI API 명세

> InnerLog 백엔드 ↔ AI 서버 연동 레퍼런스 (Claude Code용)

- **AI 서버 주소:** `http://[AI_SERVER_IP]:8001` (v2에서 8000 → 8001로 변경)
- **명세 기준일:** 2026-08-16 (v2)
- 우리 백엔드는 이 AI 서버를 HTTP로 **호출만** 한다. (AI 로직은 별도 프로세스)

> ⚠️ **v2 반영 현황**
>
> - **회고(chat) 관련 — `1. /chat`, `4. /summarize` 는 v2 기준으로 갱신됨.**
> - **스피치 관련 — `2. /question-extract`, `3. /speech-analyze` 는 아직 v1 기준 문서이며 백엔드 코드도 미대응.** v2에서 아래가 바뀌었으므로 후속 작업 필요:
>   - `/question-extract`: 응답 `questions[].text` → **`question`**, 총 12개(인성 4 / 기술 4 / 공통 4), 자소서 50자 미만이면 400
>   - `/speech-analyze`: 요청 `audio_file_path` → **`audio_path`**, 응답 구조 변경(`star_score`가 `{present, comment}` 객체, 최상위 `feedback` 제거 → `content.overall`, `coherence`가 `{summary, detail}` 객체, `content.question_type` 추가)

---

## 공통 사항

- **Content-Type:** `application/json`
- 모든 요청/응답은 JSON.
- **서버 상태 확인:** `GET /health` → `{"status": "ok"}`

---

## 1. `POST /chat` — 회고 챗봇 대화

백엔드가 매 턴마다 `state`를 **통째로** 전달하고, AI가 `ai_response` + `updated_state`를 반환한다.

> **백엔드 구현 핵심** > `state` 내용을 해석할 필요 없음. DB에 저장해 두고 다음 턴에 **그대로** 전달만 하면 됨.

### 요청

```json
{
  "session_id": "abc123",
  "user_message": "카카오 1차 면접에서 기술 질문에 막혔어요",
  "state": {
    "stage": "FACT",
    "stage_turn_count": 0,
    "total_turn_count": 0,
    "company": null,
    "role": null,
    "rejection_stage": null,
    "hypothesis": "",
    "self_blame_count": 0,
    "history": []
  }
}
```

> **첫 턴(오프닝):** `user_message`를 **빈 문자열(`""`)** 로 보내면 AI가 먼저 인사 메시지를 생성한다.
> (v1에서는 빈 문자열이 거부되어 백엔드가 트리거 문구를 넣는 workaround를 썼는데, v2에서는 불필요하다.)

### 응답

```json
{
  "ai_response": "카카오 1차 면접에서 기술 질문을 받으셨군요. 그 질문이 구체적으로 무엇이었는지 말씀해 주실 수 있을까요?",
  "updated_state": {
    "stage": "FACT",
    "stage_turn_count": 1,
    "total_turn_count": 1,
    "company": "카카오",
    "role": null,
    "rejection_stage": "1차면접",
    "hypothesis": "",
    "self_blame_count": 0,
    "history": [
      { "role": "user", "content": "카카오 1차 면접에서 기술 질문에 막혔어요" },
      {
        "role": "assistant",
        "content": "카카오 1차 면접에서 기술 질문을 받으셨군요. 그 질문이 구체적으로 무엇이었는지 말씀해 주실 수 있을까요?"
      }
    ]
  }
}
```

### `state` 필드 설명

| 필드               | 타입           | 설명                                            |
| ------------------ | -------------- | ----------------------------------------------- |
| `stage`            | string         | `FACT` / `INTERPRETATION` / `STRATEGY` / `DONE` |
| `stage_turn_count` | int            | 현재 단계에서 진행된 턴 수                      |
| `total_turn_count` | int            | 전체 대화 턴 수                                 |
| `company`          | string \| null | 자동 추출된 회사명                              |
| `role`             | string \| null | 자동 추출된 직무                                |
| `rejection_stage`  | string \| null | 탈락 단계                                       |
| `hypothesis`       | string         | 탈락 원인 가설                                  |
| `self_blame_count` | int            | 자기비난 감지 횟수                              |
| `history`          | array          | 전체 대화 히스토리                              |

> `stage`가 `DONE`이 되면 [`/summarize`](#4-post-summarize--면접-회고-요약)를 호출해서 최종 요약을 받으면 됨.

---

## 2. `POST /question-extract` — 예상 질문 생성

### 요청

```json
{
  "company": "카카오",
  "role": "백엔드 개발자",
  "resume_text": "자소서 문항1 내용...\n\n자소서 문항2 내용..."
}
```

### 응답

```json
{
  "questions": [
    { "text": "Spring Boot 프로젝트에서 가장 어려웠던 기술적 문제는 무엇이었나요?", "category": "기술" },
    { "text": "팀 프로젝트에서 API 설계 과정 중 갈등이 생겼을 때 어떻게 해결하셨나요?", "category": "인성" },
    { "text": "카카오에 지원한 이유가 무엇인가요?", "category": "공통" }
  ]
}
```

- `category` 허용값: `인성` / `기술` / `공통`
- ⚠️ **응답 시간: 30초~1분** (RAG 검색 + LLM 호출) → 백엔드 httpx timeout 넉넉히 설정 필요.

---

## 3. `POST /speech-analyze` — 스피치 분석

### 요청

```json
{
  "audio_file_path": "/uploads/audio/abc123.wav",
  "question_text": "팀 프로젝트에서 갈등이 생겼을 때 어떻게 해결하셨나요?"
}
```

### 응답

```json
{
  "acoustic": {
    "speed_wpm": 78.0,
    "speed_label": "평균(90.14어절/분)보다 느린 편이에요",
    "filler_words": { "그": 1 },
    "silence_count": 0,
    "duration_sec": 86.2,
    "word_count": 112
  },
  "content": {
    "star_score": {
      "situation": true,
      "task": false,
      "action": true,
      "result": true
    },
    "coherence": "논리 흐름 양호",
    "keyword_repeat": {},
    "negative_reframe": {
      "detected": true,
      "expressions": ["발표에 약한 편이에요"],
      "feedback": "면접에서 약점을 직접 드러내는 표현이 있어요. 굳이 언급하지 않는 것이 좋아요."
    }
  },
  "feedback": {
    "star_detail": {
      "situation": {
        "present": true,
        "excerpt": "해당 발췌 문장",
        "comment": "상황이 잘 설명되어 있어요."
      },
      "task": {
        "present": false,
        "excerpt": null,
        "comment": "과제/목표가 명시되지 않았어요. 한 문장 추가해보세요."
      },
      "action": {
        "present": true,
        "excerpt": "해당 발췌 문장",
        "comment": "구체적인 행동이 잘 드러나 있어요."
      },
      "result": {
        "present": true,
        "excerpt": "해당 발췌 문장",
        "comment": "결과가 명확하게 언급되어 있어요."
      }
    },
    "star_overall": "전체적으로 STAR 흐름이 잘 잡혀 있어요. Task 부분만 보완하면 됩니다.",
    "coherence_detail": "결론이 자연스럽게 마지막에 위치해 있어요.",
    "overall": "답변 구조가 좋습니다. Task를 추가하고 결과에 수치를 넣으면 더 설득력 있어요."
  }
}
```

### 변경사항 (v1 → v2)

| 항목                | 변경 내용                     |
| ------------------- | ----------------------------- |
| `sentiment`         | ❌ 제거 (긍정/중립/부정 비율) |
| `connectives_count` | ❌ 제거 (논리 연결어 횟수)    |
| `negative_reframe`  | ✅ 추가 (약점 노출 표현 감지) |

> - **`feedback` 필드 전체 DB 저장 필요** (재조회 가능해야 함 — 확인 완료)
> - `negative_reframe` 미감지 시: `{"detected": false, "expressions": [], "feedback": null}`

---

## 4. `POST /summarize` — 면접 회고 요약

`stage`가 `DONE`에 도달했을 때 호출.

### 요청

```json
{
  "session_id": "abc123",
  "history": [
    { "role": "assistant", "content": "방금 어떤 면접을 보셨나요?" },
    { "role": "user", "content": "카카오 백엔드 1차 면접에서 기술 질문에 막혔어요" },
    { "role": "...", "content": "..." }
  ]
}
```

### 응답

```json
{
  "session_id": "abc123",
  "company": "카카오",
  "role": "백엔드",
  "interview_type": "1차면접",
  "result": null,
  "analysis": {
    "summary": "카카오 백엔드 1차 면접. DB 인덱스 관련 기술 질문에서 어려움을 겪음.",
    "hypothesis": "DB 인덱스의 동작 원리와 실제 사용 사례에 대한 이해 부족",
    "strengths": "인덱스의 기본 개념에 대해 설명을 시작할 수 있었음",
    "weaknesses": ["인덱스 동작 원리 깊이 있는 이해 부족", "실제 쿼리 최적화 사례 설명 능력 부족"],
    "gap_analysis": "실무 사례 기반 구체적 답변 준비 여부",
    "actions": ["DB 인덱스 B-tree/Hash 원리 학습", "실제 쿼리 최적화 사례 정리", "기술 면접 답변 STAR 기법 연습"]
  }
}
```

**v1 → v2 변경점**

| 항목 | v1 | v2 |
| --- | --- | --- |
| 6개 분석 항목 | 최상위 평면 | **`analysis` 객체로 중첩** |
| 면접 단계 | `interview_stage` (`"1차"`) | **`interview_type`** (`"1차면접"` / `"2차면접"` / `"최종면접"`, 그 외 null) |

> `interview_type` 외 값은 null 처리된다. `result`(합격/탈락)는 백엔드 협의 중 필드.
>
> 백엔드는 `analysis` 안의 6개 항목만 사용하고 `company`/`role`/`interview_type`은 자체 DB 값으로 채운다.
> 파싱은 전환기 동안 v1(평면) 응답도 함께 수용한다 (`app/services/retrospect.py`의 `summarize_retrospect`).

---

## 5. `PATCH /result-update` — 면접 결과 업데이트

### 요청

```json
{
  "session_id": "abc123",
  "result": "탈락"
}
```

### 응답

```json
{
  "session_id": "abc123",
  "result": "탈락",
  "updated": true
}
```

- `result` 허용값: `"합격"` / `"탈락"`

---
