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
| `sync_app.py`       | 비교용 동기 백엔드 앱. 측정 대상 라우트만 리팩토링 이전 동작(동기 `def`)으로 교체 |
| `run.sh`            | 처리량 실험 원클릭 실행 (일회용 DB 컨테이너 포함)                            |
| `isolation.py`      | 장애 격리 실험 드라이버 (스피치 분석 배경 부하 + 다른 API 프로브). 아래 별도 절 참고 |
| `run_isolation.sh`  | 장애 격리 실험 원클릭 실행 (일회용 DB 컨테이너 포함)                         |

## 측정 대상 엔드포인트

`POST /speech-practices/{application_id}/questions` (`generate_more_questions`)
— 반복 호출 가능하고, **AI 호출(2초) 동안 DB 커넥션을 점유**하는 경로.

---

## 실행하기

`run.sh` 하나가 일회용 DB 기동 → 목 AI 기동 → 백엔드 기동 → 시드 → 부하 스윕 → 자동 정리.
DB는 매 실행마다 새로 띄우는 컨테이너(`127.0.0.1:5433`)라 로컬 개발 DB와 무관하다.

```bash
# 개선 후(비동기, 현재 코드) 측정  → results/async.json
./loadtest/run.sh async

# 개선 전(동기, baseline) 재현 → results/sync.json
#   loadtest/sync_app.py 로 측정 대상 라우트만 동기 def 로 바꿔 띄운다 (리팩토링 이전 동작)
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
docker run -d --name innerlog-loadtest-db -e POSTGRES_USER=loadtest -e POSTGRES_PASSWORD=loadtest \
  -e POSTGRES_DB=loadtest -p 127.0.0.1:5433:5432 postgres:16-alpine          # 0) DB
export DATABASE_URL=postgresql://loadtest:loadtest@127.0.0.1:5433/loadtest
alembic upgrade head
AI_DELAY_SECONDS=2.0 uvicorn loadtest.mock_ai_server:app --port 9000 &   # 1) 목 AI
AI_SERVER_URL=http://localhost:9000 \
  uvicorn app.main:app --port 8000 &                  # 2) 백엔드 (동기 비교는 loadtest.sync_app:app)
python -m loadtest.seed --apps 100                    # 3) 시드
python -m loadtest.loadgen --label async --duration 20 --levels 5,10,15,20,30,50,100   # 4) 부하
docker rm -f innerlog-loadtest-db                     # 5) 정리
```

## 해석 포인트

- **sync**: 단일 워커 + 동기 `httpx.Client` + AI 호출 내내 DB 커넥션 점유.
  커넥션 풀(기본 5+10=15) / anyio 스레드풀(40)이 상한 → RPS가 `유효커넥션/지연`
  근처에서 포화, 동시성을 올려도 p95만 치솟는다.
- **async**: `async def` + `httpx.AsyncClient`, 외부 호출 전 커넥션 반환, DB 단계는 스레드에서 실행.
  2초 대기가 이벤트 루프에서 다중화 → 동시성을 올려도 p95는 2~4초 대에서 안정적(고동시성에서도 ~4초),
  RPS가 선형에 가깝게 증가.

---

## 장애 격리 실험 (스피치 분석 sync → async)

스피치 분석(`POST /speech-practices/questions/{question_id}/submissions`)은 AI 응답에
실측 약 110초가 걸린다. 이 요청이 몰릴 때 **다른 API가 얼마나 영향을 받는지**를 측정한다.

- **배경 부하:** 스피치 분석 요청을 동시에 N건(0·5·10·15·20·30) 반복. 목 AI 지연 60초
- **프로브:** 그동안 `GET /applications` 를 동시성 10으로 90초간 반복해 처리량·p95·실패율 측정
- DB는 매 실행마다 새로 띄우는 일회용 컨테이너(`127.0.0.1:5433`)라 로컬 개발 DB와 무관하다.

```bash
# 현재 체크아웃된 코드 측정 → results/isolation_async.json
./loadtest/run_isolation.sh isolation_async

# 전환 전(동기) 코드 재현: 스피치 라우터·서비스만 전환 이전 커밋으로 되돌려 측정한 뒤 원복
git checkout 450302a -- app/api/speech.py app/services/speech.py
./loadtest/run_isolation.sh isolation_sync
git checkout HEAD -- app/api/speech.py app/services/speech.py

# 비교표
source venv/bin/activate && python -m loadtest.isolation compare isolation_sync isolation_async
```

빠르게 확인만 하려면 `LEVELS=0,15 DURATION=20 SPEECH_DELAY=40 ./loadtest/run_isolation.sh quick`.

### 출력 읽는 법

```
  bg | probe rps    p50ms    p95ms   fail  fail% |  bg ok bg fail  errors
  15 |      0.39    228.4  29827.6     33  42.3% |     30       0  probe:http_500=20,...
```

- `bg` 배경 스피치 분석 동시성 · `probe rps/p95ms/fail%` 다른 API의 처리량·지연·실패율
- `bg ok/fail` 레벨 동안 완료된 스피치 분석 수 / 실패 수
- `http_500` 은 커넥션 풀 고갈(`QueuePool limit ... reached`), `ReadError` 는 500 직후 서버가 닫은
  keep-alive 연결을 클라이언트가 재사용하다 난 실패, `ReadTimeout` 은 요청 타임아웃(프로브 60초 / 배경 240초) 초과.
