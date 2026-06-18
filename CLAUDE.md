# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

InnerLog backend — a FastAPI service for tracking tech-job applications (지원현황) and running AI-assisted interview "speech practice" (예상 질문 생성). PostgreSQL via SQLAlchemy 2.0 + Alembic. An external AI server generates expected interview questions.

## Commands

The project uses a checked-out `venv/`. Activate it first: `source venv/bin/activate`.

- Run dev server: `uvicorn app.main:app --reload --port 8000` (note: the `__main__` block in `app/main.py` uses the wrong import string `main:app`; always launch with `app.main:app`)
- Install deps: `pip install -r requirements.txt`
  - **`bcrypt` and `uvicorn` are imported/used but missing from `requirements.txt`.** They are present in `venv/`. Add them to requirements if you touch dependency setup.
- Migrations (Alembic, config in `alembic.ini`, env in `alembic/env.py`):
  - Apply: `alembic upgrade head`
  - Autogenerate after model changes: `alembic revision --autogenerate -m "message"`
  - Roll back one: `alembic downgrade -1`
  - `alembic/env.py` pulls the DB URL from `settings.DATABASE_URL` (not `alembic.ini`, whose `sqlalchemy.url` is intentionally blank) and imports `app.models` so all tables register on `Base.metadata`.

There is **no test suite** in this repo — do not assume `pytest` wiring exists.

### Environment

`.env` (gitignored) supplies `pydantic-settings` in `app/core/config.py`. Required keys:

- `DATABASE_URL` — PostgreSQL DSN (psycopg2)
- `SECRET_KEY` — JWT signing secret (HS256)
- `AI_SERVER_URL` — base URL of the external AI question-generation server

## Architecture

Strict layered flow, one module per domain (`auth`, `application`, `speech`):

```
app/api/<domain>.py        → routers: thin, parse request, call service, build response
app/services/<domain>.py   → business logic, all DB queries, raises domain exceptions
app/models/<domain>.py     → SQLAlchemy 2.0 ORM (Mapped/mapped_column, UUID PKs)
app/schemas/<domain>.py    → Pydantic request/response models
app/core/                  → config, database (engine/session/Base), exceptions
app/api/docs/<domain>.py   → per-route OpenAPI metadata (see below)
```

Routers are registered by iterating a list in `app/main.py`; each router sets its own `prefix` and `tags`. Services receive `db: Session` and `user_id` as plain args (not FastAPI dependencies) so they stay framework-light.

### Error handling — extend exceptions, don't raise raw HTTPException

All domain errors subclass `InnerLogException` (`app/core/exceptions.py`), which carries a structured `detail = {"code", "message"}`. A single handler in `main.py` serializes that detail to JSON. To add an error case: add a subclass in `exceptions.py` with its `status_code`/`code`/Korean `message`, then raise it from the service.

### OpenAPI docs are decoupled from routes

Per-route summary/description/response examples live as dicts in `app/api/docs/<domain>.py` and are spread into decorators: `@router.post(..., **create_application_docs)`. Error-response examples are **generated from the exception classes themselves** via `error_response(description, *ExceptionClasses)` in `app/api/docs/responses.py` — so docs stay in sync with `exceptions.py` automatically. When adding a route, add a matching docs dict and reference the relevant exception classes there.

### Auth

JWT (HS256, python-jose) in `app/services/auth.py`. Tokens carry `type` = `access` (30 min) or `refresh` (7 days); `/auth/refresh` rotates both. `get_current_user` in `app/api/deps.py` is the `HTTPBearer` dependency that validates the access token and loads the `User`. Passwords hashed with bcrypt.

### Data model & ownership

PostgreSQL-specific types (`UUID(as_uuid=True)`, `ARRAY`) — all PKs are server-side `uuid4`. Core graph: `User` → `Application` (지원현황) → `Question` / `PersonalStatement` / `Session`, plus `Submission` → speech/interview analysis tables. Enums (`StageEnum`, `ApplicationStatusEnum`, `PartEnum`, `LevelEnum`) are stored as SQLAlchemy `Enum`; **`StageEnum` values are Korean strings** (e.g. `"서류전형"`). Services enforce ownership by always filtering on both the resource id **and** `user_id` (see `_get_owned_application`).

### AI server integration & speech-practice gating

`app/services/speech.py` calls the external AI server (`POST {AI_SERVER_URL}/question-extract`) via `httpx` (90s timeout) to extract expected interview questions from concatenated 자기소개서 text; any HTTP/parse failure is wrapped as `AIServerError` (502). Speech practice is only allowed for specific `(stage, status)` combinations defined in the `ALLOWED_STAGES` set at the top of that file — change gating there. `create_speech_practice` is one-shot per application; `generate_more_questions` re-calls the AI and appends only questions whose text isn't already stored.

## AI API 명세 (단일 진실 공급원)

docs/ai_api.md is the full contract of the external AI server (all endpoints + request/response shapes). This backend currently integrates only a subset of it (see AI server integration above) — treat the spec as the source of truth for request/response formats and timeouts, not as a checklist of what's already wired up.

@docs/ai_api.md
