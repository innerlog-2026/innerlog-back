"""speech analysis v2 structure

Revision ID: 1e9926a8107c
Revises: 789985e24523
Create Date: 2026-08-14

AI API v2의 /speech-analyze 응답 구조 변경을 반영

- star_score: Boolean 4개 -> JSONB 1개 ({situation|task|action|result: {present, comment}})
  행동형 질문이 아니면 전체 NULL. 외부 명세가 자주 바뀌어 JSONB 로 흡수하되,
  앱이 의존하는 불변식(4개 키 존재 + present 가 boolean)만 CHECK 로 강제
- coherence: String -> JSONB ({summary, detail})
- question_type / overall 추가 (v2 는 최상위 feedback 이 없고 content.overall 로 통합)
- speech_analysis.feedback 제거
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '1e9926a8107c'
down_revision: Union[str, Sequence[str], None] = '789985e24523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAR_CHECK = (
    "star_score IS NULL OR ("
    " jsonb_typeof(star_score) = 'object'"
    " AND jsonb_exists_all(star_score, ARRAY['situation','task','action','result'])"
    " AND jsonb_typeof(star_score->'situation'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'task'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'action'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'result'->'present') = 'boolean'"
    ")"
)
_COHERENCE_CHECK = (
    "coherence IS NULL OR ("
    " jsonb_typeof(coherence) = 'object'"
    " AND jsonb_exists(coherence, 'summary')"
    ")"
)


def upgrade() -> None:
    """Upgrade schema."""
    # v2 에는 최상위 feedback 이 없음 (content.overall 로 통합)
    op.drop_column('speech_analysis', 'feedback')

    op.add_column('speech_content', sa.Column('question_type', sa.String(), nullable=True))
    op.add_column('speech_content', sa.Column('star_score', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('speech_content', sa.Column('overall', sa.Text(), nullable=True))

    # 기존 Boolean 4개를 JSONB 로 이관 (comment 는 v1 에 없으므로 null)
    op.execute(
        """
        UPDATE speech_content
        SET star_score = jsonb_build_object(
            'situation', jsonb_build_object('present', COALESCE(star_situation, false), 'comment', NULL),
            'task',      jsonb_build_object('present', COALESCE(star_task, false),      'comment', NULL),
            'action',    jsonb_build_object('present', COALESCE(star_action, false),    'comment', NULL),
            'result',    jsonb_build_object('present', COALESCE(star_result, false),    'comment', NULL)
        )
        WHERE star_situation IS NOT NULL
           OR star_task IS NOT NULL
           OR star_action IS NOT NULL
           OR star_result IS NOT NULL
        """
    )

    op.drop_column('speech_content', 'star_situation')
    op.drop_column('speech_content', 'star_task')
    op.drop_column('speech_content', 'star_action')
    op.drop_column('speech_content', 'star_result')

    # coherence: 문자열 -> {summary, detail} 객체
    op.execute(
        """
        ALTER TABLE speech_content
        ALTER COLUMN coherence TYPE jsonb
        USING (
            CASE WHEN coherence IS NULL THEN NULL
                 ELSE jsonb_build_object('summary', coherence, 'detail', NULL)
            END
        )
        """
    )

    # 데이터 이관이 끝난 뒤 제약을 추가
    op.create_check_constraint('ck_speech_content_star_score', 'speech_content', _STAR_CHECK)
    op.create_check_constraint('ck_speech_content_coherence', 'speech_content', _COHERENCE_CHECK)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_speech_content_coherence', 'speech_content', type_='check')
    op.drop_constraint('ck_speech_content_star_score', 'speech_content', type_='check')

    op.execute(
        """
        ALTER TABLE speech_content
        ALTER COLUMN coherence TYPE varchar
        USING (coherence->>'summary')
        """
    )

    op.add_column('speech_content', sa.Column('star_situation', sa.Boolean(), nullable=True))
    op.add_column('speech_content', sa.Column('star_task', sa.Boolean(), nullable=True))
    op.add_column('speech_content', sa.Column('star_action', sa.Boolean(), nullable=True))
    op.add_column('speech_content', sa.Column('star_result', sa.Boolean(), nullable=True))
    op.execute(
        """
        UPDATE speech_content
        SET star_situation = (star_score->'situation'->>'present')::boolean,
            star_task      = (star_score->'task'->>'present')::boolean,
            star_action    = (star_score->'action'->>'present')::boolean,
            star_result    = (star_score->'result'->>'present')::boolean
        WHERE star_score IS NOT NULL
        """
    )

    op.drop_column('speech_content', 'overall')
    op.drop_column('speech_content', 'star_score')
    op.drop_column('speech_content', 'question_type')

    op.add_column('speech_analysis', sa.Column('feedback', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
