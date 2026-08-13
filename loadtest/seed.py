"""
부하테스트 시드 스크립트.

- 테스트 유저 1명 + JWT access token 발급
- 허용 단계(ALLOWED_STAGES)에 해당하는 지원현황 N개 생성
- 각 지원현황에 자소서(PersonalStatement) 2개 + 목 AI가 돌려줄 질문 텍스트를 미리 심음
  → generate_more_questions 호출 시 dedup 으로 added_count=0 (steady-state, 요청당 부하 일정)

결과를 loadtest/seed_data.json 으로 저장한다 (loadgen 이 읽음).

실행:
    source venv/bin/activate
    python -m loadtest.seed --apps 100
"""
import argparse
import json
import os
import uuid

from app.core.database import SessionLocal
from app.models.application import (
    Application,
    ApplicationStatusEnum,
    PersonalStatement,
    Question,
    StageEnum,
)
from app.models.user import PartEnum, User
from app.services.auth import create_access_token, hash_password

# mock_ai_server 가 돌려주는 질문과 동일 (steady-state dedup용)
_FIXED_QUESTION_TEXTS = [
    "Spring Boot 프로젝트에서 가장 어려웠던 기술적 문제는 무엇이었나요?",
    "팀 프로젝트에서 갈등이 생겼을 때 어떻게 해결하셨나요?",
    "우리 회사에 지원한 이유가 무엇인가요?",
]

OUT_PATH = os.path.join(os.path.dirname(__file__), "seed_data.json")


def seed(num_apps: int, base_url: str) -> None:
    db = SessionLocal()
    try:
        email = f"loadtest+{uuid.uuid4().hex[:8]}@example.com"
        user = User(
            email=email,
            password=hash_password("password123!"),
            name="loadtest",
            part=PartEnum.BACK,
        )
        db.add(user)
        db.flush()

        app_ids: list[str] = []
        for _ in range(num_apps):
            application = Application(
                user_id=user.user_id,
                company_name="테스트회사",
                position="백엔드 개발자",
                stage=StageEnum.FIRST_INTERVIEW,
                status=ApplicationStatusEnum.PREPARING,  # (FIRST_INTERVIEW, PREPARING) ∈ ALLOWED_STAGES
            )
            db.add(application)
            db.flush()
            app_ids.append(str(application.application_id))

            db.add_all(
                [
                    PersonalStatement(
                        application_id=application.application_id,
                        question="지원 동기를 작성해주세요.",
                        content="저는 백엔드 개발에 관심이 많아 " * 20,
                        sequence=1,
                    ),
                    PersonalStatement(
                        application_id=application.application_id,
                        question="가장 어려웠던 프로젝트 경험은?",
                        content="대용량 트래픽 처리 경험을 통해 " * 20,
                        sequence=2,
                    ),
                ]
            )
            # 목 AI가 돌려줄 질문을 미리 심어 dedup → steady-state
            db.add_all(
                [
                    Question(
                        application_id=application.application_id,
                        question=text,
                        category="기술",
                        sequence=i,
                    )
                    for i, text in enumerate(_FIXED_QUESTION_TEXTS, start=1)
                ]
            )

        db.commit()

        token = create_access_token(str(user.user_id))
        data = {
            "base_url": base_url,
            "email": email,
            "access_token": token,
            "application_ids": app_ids,
        }
        with open(OUT_PATH, "w") as f:
            json.dump(data, f, indent=2)
        print(f"seeded user={email} apps={len(app_ids)} → {OUT_PATH}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps", type=int, default=100)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    seed(args.apps, args.base_url)
