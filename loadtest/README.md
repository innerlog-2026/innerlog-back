# 부하테스트 하네스 (sync → async 동시성 실험)

InnerLog 백엔드의 **외부 AI 호출 구간 동시성**을 측정한다. 목표는 리팩토링
(동기 blocking I/O → 비동기 I/O + 외부 호출 중 DB 커넥션 미점유) 전후의
정량 수치(RPS·p95·동시성 임계점)를 뽑는 것.

## 구성

| 파일                | 역할                                                                         |
| ------------------- | ---------------------------------------------------------------------------- |
| `mock_ai_server.py` | 고정 지연(기본 2초)만 흉내내는 목 AI 서버. 실제 LLM 비용/변동 제거           |
| `seed.py`           | 테스트 유저·토큰·지원현황(허용 단계)+자소서+질문 시드 → `seed_data.json`     |
| `loadgen.py`        | 설치 불필요한 async 부하 드라이버. 동시성 레벨 스윕 → `results/<label>.json` |
| `compare.py`        | before/after 결과 비교표                                                     |

## 측정 대상 엔드포인트

`POST /speech-practices/{application_id}/questions` (`generate_more_questions`)
— 반복 호출 가능하고, **AI 호출(2초) 동안 DB 커넥션을 점유**하는 경로.

---

## 실행하기

`run.sh` 하나가 DB 확인 → 목 AI 기동 → 백엔드 기동 → 시드 → 부하 스윕 → 자동 정리

```bash
# 개선 후(비동기) 측정  → results/async.json
./loadtest/run.sh async

# 개선 전(동기, baseline) 재현 → results/sync.json
#   SPEECH_SYNC=1 로 백엔드가 동기 def 라우트로 뜬다 (리팩토링 이전 동작)
./loadtest/run.sh sync

# 두 결과 비교표
source venv/bin/activate && python -m loadtest.compare sync async
```

빠르게 감만 보고 싶으면 레벨·시간을 줄여서:

```bash
LEVELS=5,15,30,50,100 DURATION=10 ./loadtest/run.sh sync
```

`sync`는 동시성 100에서 무너지고(성공 0 / 실패 100), `async`는 실패 0으로
36 RPS 근처까지 오르는 걸 **직접** 볼 수 있다.

### 출력 읽는 법

```
 conc      rps     p50ms     p95ms     p99ms      ok   fail  errors
    50     4.66   9508.0   13959.2   14975.1     135      0  -   ← 동기: p95가 14초로 폭발
    50    20.21   2198.4    3018.7    3040.6     443      0  -   ← 비동기: p95 3초, RPS 4배
```

- `conc` 동시 요청 수 · `rps` 초당 처리량(↑좋음) · `p95ms` 95% 지연(↓좋음)
- `fail`>0 이면 그 동시성에서 서버가 감당 못 한 것. 동기는 100에서 `http_500`(커넥션 풀 고갈) + `ReadTimeout`.

---

## 수동 실행 (스크립트 안 쓰고 단계별로)

```bash
source venv/bin/activate
docker compose up -d && alembic upgrade head          # 0) DB
AI_DELAY_SECONDS=2.0 uvicorn loadtest.mock_ai_server:app --port 9000 &   # 1) 목 AI
SPEECH_SYNC=0 AI_SERVER_URL=http://localhost:9000 \
  uvicorn app.main:app --port 8000 &                  # 2) 백엔드 (SPEECH_SYNC=1 이면 동기)
python -m loadtest.seed --apps 100                    # 3) 시드
python -m loadtest.loadgen --label async --duration 20 --levels 5,10,15,20,30,50,100   # 4) 부하
```

## 해석 포인트

- **sync**: 단일 워커 + 동기 `httpx.Client` + AI 호출 내내 DB 커넥션 점유.
  커넥션 풀(기본 5+10=15) / anyio 스레드풀(40)이 상한 → RPS가 `유효커넥션/지연`
  근처에서 포화, 동시성을 올려도 p95만 치솟는다.
- **async**: `async def` + `httpx.AsyncClient`, 외부 호출 전 커넥션 반환.
  2초 대기가 이벤트 루프에서 다중화 → 동시성을 올려도 p95는 2~4초 대에서 안정적(고동시성에서도 ~4초),
  RPS가 선형에 가깝게 증가.
