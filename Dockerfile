# InnerLog 백엔드 (FastAPI) 프로덕션 이미지
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성만 먼저 복사해 레이어 캐시 활용
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 + 마이그레이션(alembic) 복사
COPY . .

EXPOSE 8000

# 컨테이너에서는 CLI로 기동한다 (app/main.py의 __main__ 블록은 사용하지 않음)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
