"""change stage to enum

Revision ID: 204ac2d51108
Revises: 7b1a50f4104d
Create Date: 2026-06-01 10:31:09.784147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '204ac2d51108'
down_revision: Union[str, Sequence[str], None] = '7b1a50f4104d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

stageenum = postgresql.ENUM(
    'DOCUMENT', 'CODING_TEST', 'FIRST_INTERVIEW', 'SECOND_INTERVIEW', 'FINAL_INTERVIEW',
    name='stageenum',
)


def upgrade() -> None:
    """Upgrade schema."""
    stageenum.create(op.get_bind(), checkfirst=True)
    op.alter_column('application', 'stage',
               existing_type=sa.VARCHAR(),
               type_=stageenum,
               existing_nullable=True,
               postgresql_using='stage::text::stageenum')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('application', 'stage',
               existing_type=stageenum,
               type_=sa.VARCHAR(),
               existing_nullable=True)
    stageenum.drop(op.get_bind(), checkfirst=True)
