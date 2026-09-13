"""speech_content: AI v2 최종 명세 반영 (present nullable + feedback 컬럼)

Revision ID: d4f1b6c2a705
Revises: c3d5e7f9a1b2
Create Date: 2026-09-13 

AI 개발자 최종본(`/speech-analyze star_score 포맷 변경`) 기준으로 두 가지를 맞춘다.

1) 비행동형 질문에서 star_score 4개 항목이 {"present": null, "comment": null} 로 온다.
   기존 CHECK 는 present 를 boolean 으로만 허용해 의견형 답변 INSERT 가 제약 위반으로
   실패한다. boolean 또는 null 을 허용하도록 재정의한다.

2) v2 초안과 달리 최종본은 최상위 feedback 블록을 유지한다
   (star_detail 만 제거되고 star_overall / coherence_detail / overall 이 남음).
   overall 은 기존 컬럼에 담고, 나머지 두 개를 컬럼으로 추가해 유실을 막는다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd4f1b6c2a705'
down_revision: Union[str, Sequence[str], None] = 'c3d5e7f9a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CONSTRAINT = "ck_speech_content_star_score"

# present 가 boolean 또는 null 이면 통과 (비행동형 질문 대응).
# 항목 자체가 JSON null 로 오는 구버전 형태도 계속 허용해 둔다.
_NEW_CHECK = (
    "star_score IS NULL OR ("
    " jsonb_typeof(star_score) = 'object'"
    " AND jsonb_exists_all(star_score, ARRAY['situation','task','action','result'])"
    " AND COALESCE(jsonb_typeof(star_score->'situation') = 'null'"
    "          OR (jsonb_typeof(star_score->'situation') = 'object'"
    "              AND jsonb_typeof(star_score->'situation'->'present') IN ('boolean','null')), false)"
    " AND COALESCE(jsonb_typeof(star_score->'task') = 'null'"
    "          OR (jsonb_typeof(star_score->'task') = 'object'"
    "              AND jsonb_typeof(star_score->'task'->'present') IN ('boolean','null')), false)"
    " AND COALESCE(jsonb_typeof(star_score->'action') = 'null'"
    "          OR (jsonb_typeof(star_score->'action') = 'object'"
    "              AND jsonb_typeof(star_score->'action'->'present') IN ('boolean','null')), false)"
    " AND COALESCE(jsonb_typeof(star_score->'result') = 'null'"
    "          OR (jsonb_typeof(star_score->'result') = 'object'"
    "              AND jsonb_typeof(star_score->'result'->'present') IN ('boolean','null')), false)"
    ")"
)

# 이전 버전: present 는 반드시 boolean.
_OLD_CHECK = (
    "star_score IS NULL OR ("
    " jsonb_typeof(star_score) = 'object'"
    " AND jsonb_exists_all(star_score, ARRAY['situation','task','action','result'])"
    " AND jsonb_typeof(star_score->'situation'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'task'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'action'->'present') = 'boolean'"
    " AND jsonb_typeof(star_score->'result'->'present') = 'boolean'"
    ")"
)


def upgrade() -> None:
    """Upgrade schema."""
    # CHECK 는 이름으로 갈아끼운다. 1e9926a8107c 가 어떤 버전으로 만들어졌든
    # (원본이든 수정본이든) 이름이 같으므로 drop → create 로 최종 형태가 보장된다.
    op.drop_constraint(_CONSTRAINT, "speech_content", type_="check")
    op.create_check_constraint(_CONSTRAINT, "speech_content", _NEW_CHECK)

    op.add_column("speech_content", sa.Column("star_overall", sa.Text(), nullable=True))
    op.add_column("speech_content", sa.Column("coherence_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("speech_content", "coherence_detail")
    op.drop_column("speech_content", "star_overall")

    # present 가 null 인 기존 행이 있으면 되돌린 CHECK 를 만족하지 못하므로 먼저 정리한다.
    op.execute(
        "UPDATE speech_content SET star_score = NULL "
        "WHERE star_score IS NOT NULL AND NOT (" + _OLD_CHECK + ")"
    )
    op.drop_constraint(_CONSTRAINT, "speech_content", type_="check")
    op.create_check_constraint(_CONSTRAINT, "speech_content", _OLD_CHECK)
