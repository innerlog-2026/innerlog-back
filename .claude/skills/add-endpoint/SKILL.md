---
name: add-endpoint
description: >-
  Scaffold a new API endpoint or domain in the InnerLog FastAPI backend following
  its strict layered conventions. Use when adding/changing a route, service method,
  model, schema, exception, or OpenAPI docs — e.g. "새 API 추가", "엔드포인트 추가",
  "라우트 추가", "지원현황/스피치 같은 새 기능/도메인 추가", "에러 케이스 추가", "add a route/service/model".
---

# InnerLog 엔드포인트 추가 가이드

InnerLog 백엔드는 도메인(`auth`, `application`, `speech`)당 한 세트의 **엄격한 계층형 구조**를 따른다.
새 기능을 추가할 때는 아래 계층을 **항상 같은 순서·같은 규약**으로 손대야 한다. 규약을 깨면
OpenAPI 문서가 어긋나거나 Alembic 마이그레이션이 비거나 소유권 검증이 빠지는 버그가 난다.

## 계층 맵

```
app/schemas/<domain>.py    → Pydantic 요청/응답 모델
app/models/<domain>.py     → SQLAlchemy 2.0 ORM (새 테이블이 필요할 때만)
app/core/exceptions.py     → 도메인 예외 (새 에러 케이스가 있을 때만)
app/services/<domain>.py   → 비즈니스 로직 + 모든 DB 쿼리 (db, user_id를 평범한 인자로 받음)
app/api/docs/<domain>.py   → 라우트별 OpenAPI 메타데이터 dict
app/api/<domain>.py        → 얇은 라우터 (요청 파싱 → 서비스 호출 → 응답 조립)
app/main.py                → 새 도메인일 때만 라우터 등록
```

가장 가까운 기존 예시를 먼저 열어 그대로 따라 쓴다:
- 단순 1엔드포인트 도메인: `app/api/application.py`, `app/services/application.py`
- 인증·소유권·AI 연동·게이팅이 있는 복합 도메인: `app/api/speech.py`, `app/services/speech.py`

## 작업 순서 (체크리스트)

### 1. 스키마 — `app/schemas/<domain>.py`
- 요청은 `...Request`/`...Req`, 응답은 `...Response`로 네이밍.
- ORM 객체를 그대로 반환·검증할 응답 모델에는 `model_config = ConfigDict(from_attributes=True)`.
- 필드는 `Field(..., description=..., examples=[...])`로 설명/예시를 채운다 (Swagger 품질).
- enum 타입은 `app/models/<domain>.py`의 enum을 import 해서 재사용.

### 2. 모델 — `app/models/<domain>.py` (새 테이블이 필요할 때만)
- SQLAlchemy 2.0 스타일: `Mapped[...]` + `mapped_column(...)`.
- PK는 `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` (서버사이드 생성).
- PostgreSQL 전용 타입 사용: `UUID(as_uuid=True)`, 배열은 `ARRAY`.
- enum은 `SAEnum(MyEnum)`로 저장. **`StageEnum` 값은 한글 문자열**(`"서류전형"` 등)임을 잊지 말 것.
- FK·`relationship(...)`의 `back_populates`를 양쪽에 모두 건다.
- **새 모델 클래스는 반드시 `app/models/__init__.py`에 import/등록**한다. 그래야
  `Base.metadata`에 잡혀 Alembic 자동생성이 테이블을 인식한다.

### 3. 예외 — `app/core/exceptions.py` (새 에러 케이스가 있을 때만)
- **절대 raw `HTTPException`을 raise 하지 않는다.** `InnerLogException` 서브클래스를 추가한다.
- 패턴: `super().__init__(status_code, "DOMAIN_CODE", "한글 메시지")`.
- 이 클래스 하나가 (a) 서비스에서 raise할 에러, (b) OpenAPI 에러 응답 예시의 **단일 진실 공급원**이 된다.

### 4. 서비스 — `app/services/<domain>.py`
- 시그니처는 `(db: Session, user_id: uuid.UUID, ...)` — FastAPI 의존성이 아니라 **평범한 인자**로 받는다.
- **모든 DB 쿼리는 여기서.** 라우터에서 쿼리하지 않는다.
- **소유권 강제**: 사용자 소유 리소스는 항상 `리소스 id`와 `user_id`를 **둘 다** 필터한다.
  `app/services/speech.py`의 `_get_owned_application` 패턴을 재사용/복제할 것. 없으면 404 예외를 raise.
- 실패 시 3번에서 만든 도메인 예외를 raise.
- 쓰기 후에는 `db.commit()` → 필요한 객체 `db.refresh(...)`.
- 외부 AI 서버 호출이 있으면 `app/services/speech.py`의 `_extract_questions`처럼 `httpx`로 호출하고
  `(httpx.HTTPError, ValueError)`를 잡아 `AIServerError()`(502)로 감싼다. 타임아웃은 넉넉히
  (AI 응답 30초~1분).

### 5. Docs — `app/api/docs/<domain>.py`
- 라우트별로 `summary`/`description`/`responses`를 담은 dict를 만들고 `..._docs`로 이름 짓는다.
- **에러 응답은 직접 쓰지 말고** `error_response(설명, *예외클래스들)`로 생성한다
  (`app/api/docs/responses.py`). 이렇게 하면 docs가 `exceptions.py`와 자동 동기화된다.
- 자주 쓰는 응답(`_unauthorized_response` 등)은 모듈 상단에 한 번만 정의해 재사용.
- 라우트가 raise할 수 있는 모든 예외의 status code를 `responses`에 빠짐없이 매핑.

### 6. 라우터 — `app/api/<domain>.py`
- 라우터는 **얇게**: 요청 파싱 → 서비스 호출 → 응답 모델 조립. 로직/쿼리 금지.
- 데코레이터에 docs dict를 스프레드: `@router.post("", response_model=..., status_code=201, **xxx_docs)`.
- 인증이 필요한 엔드포인트는 `current_user: User = Depends(get_current_user)`를 받고
  서비스에는 `current_user.user_id`를 넘긴다.
- `db: Session = Depends(get_db)`로 세션 주입.
- 생성(201) 등 기본이 아닌 상태코드는 `status_code=`로 명시.

### 7. 라우터 등록 — `app/main.py` (새 도메인일 때만)
- `app.api`에서 새 모듈을 import 하고 `for router in [...]:` 리스트에 `<domain>.router`를 추가.
- prefix/tags는 각 라우터의 `APIRouter(prefix=..., tags=...)`에서 설정한다 (main이 아니라).

### 8. 마이그레이션 (모델을 추가·변경했을 때만)
`venv`를 먼저 활성화: `source venv/bin/activate`
- 자동생성: `alembic revision --autogenerate -m "메시지"`
- 생성된 파일을 **반드시 눈으로 검토** (자동생성이 enum 변경·인덱스 등을 놓칠 수 있음).
- 적용: `alembic upgrade head`
- DB URL은 `alembic.ini`가 아니라 `settings.DATABASE_URL`에서 온다(`alembic/env.py`).

## 검증

테스트 스위트가 없다. 변경 후 최소한 import/기동이 깨지지 않는지 확인:
- `source venv/bin/activate && uvicorn app.main:app --reload --port 8000`
  (`app/main:app`로 실행 — `app/main.py`의 `__main__` 블록은 잘못된 `main:app`을 쓴다.)
- `/docs`에서 새 라우트의 요청/응답/에러 예시가 의도대로 나오는지 확인.

## 흔한 함정

- `app/models/__init__.py`에 새 모델 등록을 빠뜨리면 Alembic이 테이블을 못 본다.
- 라우터에서 직접 DB 쿼리하거나 raw `HTTPException`을 raise하면 규약 위반.
- 소유권 필터(`user_id`)를 빠뜨리면 다른 사용자의 리소스가 노출된다.
- docs의 에러 예시를 손으로 쓰면 `exceptions.py`와 어긋난다 — 항상 `error_response(...)` 사용.
- `bcrypt`, `uvicorn`은 코드에서 쓰지만 `requirements.txt`에 빠져 있다(venv엔 있음). 의존성을
  건드린다면 추가할 것.
