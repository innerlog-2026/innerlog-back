"""drop PREPARING from application status

Revision ID: c3d5e7f9a1b2
Revises: 1e9926a8107c
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3d5e7f9a1b2'
down_revision: Union[str, Sequence[str], None] = '1e9926a8107c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 기존 PREPARING 행을 IN_PROGRESS로 병합한 뒤 라벨을 제거함.
    # (PostgreSQL은 enum 라벨 삭제를 지원하지 않아 타입 재생성으로 교체함)
    op.execute("UPDATE application SET status = 'IN_PROGRESS' WHERE status = 'PREPARING'")
    op.execute("CREATE TYPE applicationstatusenum_new AS ENUM ('IN_PROGRESS', 'COMPLETED')")
    op.execute(
        "ALTER TABLE application ALTER COLUMN status TYPE applicationstatusenum_new "
        "USING status::text::applicationstatusenum_new"
    )
    op.execute("DROP TYPE applicationstatusenum")
    op.execute("ALTER TYPE applicationstatusenum_new RENAME TO applicationstatusenum")


def downgrade() -> None:
    """Downgrade schema."""
    # 라벨만 복원함. 병합된 IN_PROGRESS 행이 어느 쪽이었는지는 복원 불가.
    op.execute(
        "CREATE TYPE applicationstatusenum_old AS ENUM ('PREPARING', 'IN_PROGRESS', 'COMPLETED')"
    )
    op.execute(
        "ALTER TABLE application ALTER COLUMN status TYPE applicationstatusenum_old "
        "USING status::text::applicationstatusenum_old"
    )
    op.execute("DROP TYPE applicationstatusenum")
    op.execute("ALTER TYPE applicationstatusenum_old RENAME TO applicationstatusenum")
