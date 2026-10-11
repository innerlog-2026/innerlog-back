"""speech_acoustic: 게이지용 기준값 필드 추가

Revision ID: e2b7a9c4d816
Revises: 88d10e99058d
Create Date: 2026-10-07

/speech-analyze 응답 acoustic 에 추가된 3개 필드를 저장함.

- speed_baseline: 말 속도 기준값 JSONB ({mean, p5, p33, p67, p95, source, sample_count})
- length_label: 답변 길이 문구 (speed_label 과 같은 3단계 문장)
- length_baseline: 답변 시간 기준값 JSONB ({mean, p5, p33, p67, p95, unit, source, sample_count})

speed_label/length_label 문구에 평균값이 포함되므로 문구와 함께 생성 시점의 기준값을 저장함.
기존 행은 NULL 로 남음.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e2b7a9c4d816'
down_revision: Union[str, Sequence[str], None] = '88d10e99058d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('speech_acoustic', sa.Column('speed_baseline', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('speech_acoustic', sa.Column('length_label', sa.String(), nullable=True))
    op.add_column('speech_acoustic', sa.Column('length_baseline', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('speech_acoustic', 'length_baseline')
    op.drop_column('speech_acoustic', 'length_label')
    op.drop_column('speech_acoustic', 'speed_baseline')
