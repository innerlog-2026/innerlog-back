"""rework speech analysis tables for AI v2 /speech-analyze response

Revision ID: b7c8d9e0f1a2
Revises: a1c4e9d2f3b8
Create Date: 2026-06-18 00:00:00.000000

기존 speech_analysis/acoustic/content 테이블은 AI v1 응답 기준이라 v2 응답과 맞지 않았다.
- 수치형(speed_wpm, duration_sec)은 float
- 맵/중첩 구조(filler_words, keyword_repeat, negative_reframe, feedback)는 JSONB
- v2에서 제거된 connectives_count 컬럼 삭제
세 테이블에는 적재된 데이터가 없으므로 호환 불가 컬럼은 drop 후 재생성한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a1c4e9d2f3b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # speech_analysis.feedback: Text -> JSONB (feedback 객체 전체 저장)
    op.drop_column('speech_analysis', 'feedback')
    op.add_column('speech_analysis', sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # speech_acoustic: 수치형 float화, filler_words 맵(JSONB)화
    op.alter_column('speech_acoustic', 'speed_wpm', existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)
    op.alter_column('speech_acoustic', 'duration_sec', existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=True)
    op.drop_column('speech_acoustic', 'filler_words')
    op.add_column('speech_acoustic', sa.Column('filler_words', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # speech_content: connectives_count 제거, keyword_repeat 맵화, negative_reframe 객체화
    op.drop_column('speech_content', 'connectives_count')
    op.drop_column('speech_content', 'keyword_repeat')
    op.add_column('speech_content', sa.Column('keyword_repeat', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.drop_column('speech_content', 'negative_reframe')
    op.add_column('speech_content', sa.Column('negative_reframe', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('speech_content', 'negative_reframe')
    op.add_column('speech_content', sa.Column('negative_reframe', sa.Text(), nullable=True))
    op.drop_column('speech_content', 'keyword_repeat')
    op.add_column('speech_content', sa.Column('keyword_repeat', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('speech_content', sa.Column('connectives_count', sa.Integer(), nullable=True))

    op.drop_column('speech_acoustic', 'filler_words')
    op.add_column('speech_acoustic', sa.Column('filler_words', postgresql.ARRAY(sa.String()), nullable=True))
    op.alter_column('speech_acoustic', 'duration_sec', existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)
    op.alter_column('speech_acoustic', 'speed_wpm', existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=True)

    op.drop_column('speech_analysis', 'feedback')
    op.add_column('speech_analysis', sa.Column('feedback', sa.Text(), nullable=True))
