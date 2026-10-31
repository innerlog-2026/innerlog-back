#!/usr/bin/env bash
#
# 부하테스트 실행 스크립트 (예상 질문 추가 생성 sync → async 처리량 실험)
#
#   ./loadtest/run.sh async      # 현재 코드(비동기) 측정  → results/async.json
#   ./loadtest/run.sh sync       # 동기 버전(loadtest/sync_app.py) 측정 → results/sync.json
#   ./loadtest/run.sh sync mylabel   # 결과 파일 이름 직접 지정
#
# 하는 일:
#   1) 일회용 PostgreSQL 컨테이너 기동 (127.0.0.1:${LT_DB_PORT}) + 스키마 마이그레이션
#   2) Mock AI 서버 기동 (포트 9000, 고정 지연 ${AI_DELAY}초)
#   3) 백엔드 기동 (포트 8000, uvicorn 단일 워커, sync/async 앱 선택)
#   4) 헬스체크 → 테스트 데이터 시드 → 동시성 스윕 부하
#   5) 끝나면 백엔드·목서버·DB 컨테이너 정리
#
set -euo pipefail

MODE="${1:-async}"          # sync | async
LABEL="${2:-$MODE}"         # 결과 파일 이름
DURATION="${DURATION:-20}"  # 레벨당 초
LEVELS="${LEVELS:-5,10,15,20,30,50,100}"
AI_DELAY="${AI_DELAY_SECONDS:-2.0}"
LT_DB_PORT="${LT_DB_PORT:-5433}"
DB_CONTAINER="innerlog-loadtest-db"

case "$MODE" in
  sync)  APP_TARGET="loadtest.sync_app:app" ;;
  async) APP_TARGET="app.main:app" ;;
  *) echo "사용법: ./loadtest/run.sh [sync|async] [label]"; exit 1 ;;
esac

cd "$(dirname "$0")/.."      # 레포 루트로 이동
# shellcheck disable=SC1091
source venv/bin/activate

for port in 8000 9000 "$LT_DB_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "포트 ${port} 사용 중 — 해당 프로세스를 종료한 뒤 다시 실행"; exit 1
  fi
done

LOG_DIR="$(mktemp -d)"
MOCK_LOG="$LOG_DIR/mock_ai.log"
BACK_LOG="$LOG_DIR/backend.log"
MOCK_PID=""
BACK_PID=""

export DATABASE_URL="postgresql://loadtest:loadtest@127.0.0.1:${LT_DB_PORT}/loadtest"

say() { printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }

cleanup() {
  say "정리: 백엔드·목서버·DB 컨테이너 종료"
  [ -n "$MOCK_PID" ] && kill "$MOCK_PID" >/dev/null 2>&1 || true
  [ -n "$BACK_PID" ] && kill "$BACK_PID" >/dev/null 2>&1 || true
  docker rm -f "$DB_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# ── 1) DB ───────────────────────────────────────────────
say "1/5  일회용 PostgreSQL 기동 + 마이그레이션"
docker rm -f "$DB_CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$DB_CONTAINER" \
  -e POSTGRES_USER=loadtest -e POSTGRES_PASSWORD=loadtest -e POSTGRES_DB=loadtest \
  -p "127.0.0.1:${LT_DB_PORT}:5432" postgres:16-alpine >/dev/null
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" pg_isready -U loadtest -d loadtest >/dev/null 2>&1; then break; fi
  sleep 0.5
done
alembic upgrade head >/dev/null 2>&1 || alembic upgrade head

# ── 2) Mock AI ─────────────────────────────────────────
say "2/5  Mock AI 서버 기동 (포트 9000, 지연 ${AI_DELAY}s)"
AI_DELAY_SECONDS="$AI_DELAY" uvicorn loadtest.mock_ai_server:app \
  --host 127.0.0.1 --port 9000 --no-access-log >"$MOCK_LOG" 2>&1 &
MOCK_PID=$!

# ── 3) 백엔드 (모드 선택) ──────────────────────────────
say "3/5  백엔드 기동 (포트 8000, 모드=${MODE}, 앱=${APP_TARGET})"
AI_SERVER_URL="http://127.0.0.1:9000" \
  uvicorn "$APP_TARGET" --host 127.0.0.1 --port 8000 --no-access-log >"$BACK_LOG" 2>&1 &
BACK_PID=$!

# ── 4) 헬스체크 ────────────────────────────────────────
say "4/5  헬스체크 + 시드"
for _ in $(seq 1 40); do
  m=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9000/health 2>/dev/null || true)
  b=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || true)
  if [ "$m" = "200" ] && [ "$b" = "200" ]; then break; fi
  sleep 0.5
done
if [ "${m:-}" != "200" ] || [ "${b:-}" != "200" ]; then
  echo "서버 기동 실패. 로그: $MOCK_LOG / $BACK_LOG"; exit 1
fi
python -m loadtest.seed --apps 100

# ── 5) 부하 스윕 ───────────────────────────────────────
say "5/5  부하 스윕 (모드=${MODE}, 레벨=${LEVELS}, 레벨당 ${DURATION}s)"
python -m loadtest.loadgen --label "$LABEL" --duration "$DURATION" --levels "$LEVELS"

echo
echo "✅ 완료 → loadtest/results/${LABEL}.json"
echo "   백엔드 로그: $BACK_LOG"
