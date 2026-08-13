"""add application_stage table

Revision ID: 789985e24523
Revises: 15c9a0cd9946
Create Date: 2026-08-13 17:52:05.776274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '789985e24523'
down_revision: Union[str, Sequence[str], None] = '15c9a0cd9946'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 새로 만드는 단계별 상태 enum
stagestatusenum = postgresql.ENUM(
    'IN_PROGRESS', 'PASS', 'FAIL',
    name='stagestatusenum',
    create_type=False,
)
# application 테이블에서 이미 생성된 stage enum 재사용 (다시 만들지 않음)
stageenum = postgresql.ENUM(
    'DOCUMENT', 'CODING_TEST', 'FIRST_INTERVIEW', 'SECOND_INTERVIEW', 'FINAL_INTERVIEW',
    name='stageenum',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    stagestatusenum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'application_stage',
        sa.Column('application_stage_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('stage', stageenum, nullable=False),
        sa.Column('status', stagestatusenum, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['application.application_id'], ),
        sa.PrimaryKeyConstraint('application_stage_id'),
        sa.UniqueConstraint('application_id', 'stage', name='uq_application_stage_app_stage'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('application_stage')
    stagestatusenum.drop(op.get_bind(), checkfirst=True)
