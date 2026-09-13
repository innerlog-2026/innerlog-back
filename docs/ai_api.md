# AI API 명세

> InnerLog 백엔드 ↔ AI 서버 연동 레퍼런스 (Claude Code용)

- **AI 서버 주소:** `http://[AI_SERVER_IP]:8001` (v2에서 8000 → 8001로 변경)

> ⚠️ **백엔드의 `AI_SERVER_URL` 은 위 주소가 아니다.**
> 운영에서는 backend/ai 가 같은 compose 네트워크에 있어 **`http://ai:8000`(컨테이너 내부 포트)** 로 호출한다.
> 위 `:8001` 은 EC2 호스트에 공개된 포트(`127.0.0.1:8001 -> 컨테이너 8000`)이므로,
> `AI_SERVER_URL` 을 `:8001` 로 바꾸면 오히려 연결이 끊긴다. (v2 재배포 시에도 이 값은 변경 불필요)
- **명세 기준일:** 2026-08-16 (v2)
- 우리 백엔드는 이 AI 서버를 HTTP로 **호출만** 한다. (AI 로직은 별도 프로세스)

> **v2 반영 완료** — 아래 5개 엔드포인트 모두 v2 기준이며 백엔드도 대응 완료.

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
    { "question": "Spring Boot 프로젝트에서 가장 어려웠던 기술적 문제는 무엇이었나요?", "category": "기술" },
    { "question": "팀 프로젝트에서 API 설계 과정 중 갈등이 생겼을 때 어떻게 해결하셨나요?", "category": "인성" },
    { "question": "카카오에 지원한 이유가 무엇인가요?", "category": "공통" }
  ]
}
```

- **v1 → v2:** 응답 필드명 `text` → **`question`**
- **총 12개** 반환 (인성 4 / 기술 4 / 공통 4)
- `resume_text` 가 **50자 미만이면 400** 에러
- `category` 허용값: `인성` / `기술` / `공통`
- ⚠️ **응답 시간: 30초~1분** (RAG 검색 + LLM 호출) → 백엔드 httpx timeout 넉넉히 설정 필요.

---

## 3. `POST /speech-analyze` — 스피치 분석

음성 파일 경로를 받아 STT 변환 후 음향 + 내용 분석 반환. 백엔드는 파일을 공유 볼륨에 저장하고 **경로만** 넘긴다.

### 요청

```json
{
  "audio_file_path": "/shared/audio/ckmk_a_ict_m_e_42650.wav",
  "question_text": "팀 프로젝트에서 갈등을 해결한 경험이 있나요?"
}
```

> `question_text` 는 **선택**. 있으면 질문 유형(행동형/의견형/기술형/가정형)을 판별해 STAR 적용 여부를 결정한다.

> ⚠️ 필드명은 **`audio_file_path`** 다. AI 서버의 `SpeechAnalyzeRequest` 가 이 이름을 **필수**로 받으므로,
> `audio_path` 로 보내면 핸들러가 실행되기도 전에 Pydantic 이 **422** 를 내고 백엔드는 이를 **502** 로 감싼다.

### 응답

```json
{
  "acoustic": {
    "speed_wpm": 87.5,
    "speed_label": "적절",
    "filler_words": { "음": 2, "어": 1 },
    "silence_count": 1,
    "duration_sec": 62,
    "word_count": 90
  },
  "content": {
    "question_type": "행동형",
    "star_score": {
      "situation": { "present": true, "comment": "배경 상황이 구체적으로 설명됐습니다." },
      "task": { "present": false, "comment": "본인의 역할이 명확히 드러나지 않았습니다." },
      "action": { "present": true, "comment": "구체적인 행동이 잘 서술됐습니다." },
      "result": { "present": true, "comment": "결과가 명확히 제시됐습니다." }
    },
    "coherence": { "summary": "논리 흐름 양호", "detail": null },
    "keyword_repeat": { "프로젝트": 4 },
    "negative_reframe": { "detected": false, "expressions": [], "feedback": null }
  },
  "feedback": {
    "star_overall": "상황과 행동은 잘 설명했지만, 본인의 역할과 결과를 더 구체적으로 말해보세요.",
    "coherence_detail": null,
    "overall": "전반적으로 경험을 잘 구조화해서 설명했습니다."
  }
}
```

> **비행동형 질문(의견형/기술형/가정형)** 이면 `star_score` 의 4개 항목이 모두
> `{"present": null, "comment": null}` 로 온다. **`star_score` 자체가 null 로 오지는 않는다.**
> 이때 `feedback.star_overall` 도 null 이다. 프론트는 `content.question_type === "행동형"`
> 일 때만 STAR UI 를 노출하고, 그 외에는 `feedback.overall` 만 보여준다.

### v1 → v2(최종) 변경점

| 항목 | v1 | v2 (최종) |
| --- | --- | --- |
| 요청 오디오 경로 | `audio_file_path` | **`audio_file_path` (변경 없음)** — v2 초안에 `audio_path` 로 적혀 있던 것은 오기 |
| `star_score` | `{situation: true, …}` 단순 bool | **`{situation: {present, comment}, …}` 객체**. 항상 4개 키 존재, 비행동형이면 `present`/`comment` 가 null |
| `coherence` | 문자열 | **`{summary, detail}` 객체** |
| 최상위 `feedback` | `star_detail`/`star_overall`/… | **유지**. `star_detail` 만 제거(내용이 `star_score[*].comment` 로 흡수). 남는 필드는 `star_overall` / `coherence_detail` / `overall` |
| 종합 피드백 위치 | `feedback.overall` | **`feedback.overall`** (v2 초안에서 `content.overall` 로 옮긴다고 했으나 최종본에서 원복) |
| `content.question_type` | 없음 | **추가** (행동형/의견형/기술형/가정형) |
| `speed_label` | 문장형 | 짧은 라벨 (`느린 편`/`적절`/`빠른 편`) |
| `silence_count` | 침묵 구간 수 | **1.5초 이상** 침묵 횟수 |

> **v2 초안 → 최종 정정 (2026-09-13):** 초안에는 "최상위 `feedback` 제거 → 종합 피드백은
> `content.overall`", "행동형이 아니면 `star_score` 는 null" 로 적혀 있었다. AI 개발자
> 최종본에서 둘 다 바뀌었으므로 위 표가 최신이다.

> **백엔드 저장:** `star_score`/`coherence` 는 JSONB 로 저장하며, CHECK 제약으로 최소 구조
> (4개 키 존재 + 각 항목이 `present` 를 가진 객체이고 `present` 가 **boolean 또는 null**)를 강제한다.
> 미지의 키는 허용해 명세 확장을 흡수한다. (`app/models/submission.py`)
> `feedback.star_overall` / `feedback.coherence_detail` 은 `speech_content` 의 동명 컬럼에 저장한다.

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
