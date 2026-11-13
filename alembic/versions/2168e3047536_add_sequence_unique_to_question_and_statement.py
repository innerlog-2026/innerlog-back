"""질문/자소서 순서 유니크 제약 추가

Revision ID: 2168e3047536
Revises: e2b7a9c4d816
Create Date: 2026-11-12

스피치 연습 최초 생성과 질문 추가 생성은 DB 읽기 → AI 호출 → DB 쓰기 순서라,
읽기 이후 들어온 동시 요청도 검사를 통과해 같은 순서(sequence)로 중복 저장될 수 있음.
이를 DB 제약으로 막음.

1) question (application_id, sequence)
2) personal_statement (application_id, sequence)

이미 중복된 행이 있으면 제약을 만들 수 없으므로, 데이터를 임의로 고치지 않고
중복 현황을 담은 에러로 중단함.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2168e3047536'
down_revision: Union[str, Sequence[str], None] = 'e2b7a9c4d816'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = ('question', 'personal_statement')


def _duplicate_groups(table: str) -> int:
    """(application_id, sequence) 가 겹치는 그룹 수를 셈."""
    return op.get_bind().execute(
        sa.text(
            f"SELECT count(*) FROM ("
            f"  SELECT 1 FROM {table}"
            f"  WHERE sequence IS NOT NULL"
            f"  GROUP BY application_id, sequence HAVING count(*) > 1"
            f") AS dup"
        )
    ).scalar_one()


def upgrade() -> None:
    """Upgrade schema."""
    duplicates = {table: _duplicate_groups(table) for table in _TABLES}
    if any(duplicates.values()):
        raise RuntimeError(
            f"(application_id, sequence) 중복 그룹이 있어 유니크 제약을 만들 수 없음: {duplicates}. "
            "중복 행을 정리한 뒤 다시 실행해야 함."
        )

    op.create_unique_constraint(
        'uq_question_application_sequence', 'question', ['application_id', 'sequence']
    )
    op.create_unique_constraint(
        'uq_personal_statement_application_sequence',
        'personal_statement',
        ['application_id', 'sequence'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_personal_statement_application_sequence', 'personal_statement', type_='unique'
    )
    op.drop_constraint('uq_question_application_sequence', 'question', type_='unique')
