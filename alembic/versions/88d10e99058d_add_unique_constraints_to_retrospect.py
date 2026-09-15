"""회고 세션/분석 결과 유니크 제약 추가

Revision ID: 88d10e99058d
Revises: d4f1b6c2a705
Create Date: 2026-09-14

회고 시작/요약은 존재 확인 → AI 호출 → 저장 순서라, 존재 확인과 commit 사이(AI 응답 시간)에
들어온 동시 요청도 확인을 통과해 중복 행이 생길 수 있음. 이를 DB 제약으로 막음.

1) session (application_id, type): 한 지원의 같은 면접 단계 회고는 1개만 허용함.
2) interview_analysis (session_id): 회고 세션당 분석 결과는 1개만 허용함.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '88d10e99058d'
down_revision: Union[str, Sequence[str], None] = 'd4f1b6c2a705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_session_application_type', 'session', ['application_id', 'type']
    )
    op.create_unique_constraint(
        'uq_interview_analysis_session', 'interview_analysis', ['session_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_interview_analysis_session', 'interview_analysis', type_='unique')
    op.drop_constraint('uq_session_application_type', 'session', type_='unique')
