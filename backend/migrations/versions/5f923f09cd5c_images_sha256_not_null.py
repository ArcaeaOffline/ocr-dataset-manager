"""images sha256 not null

Revision ID: 5f923f09cd5c
Revises: b43fd2848298
Create Date: 2026-09-20 02:33:13.678372

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f923f09cd5c"
down_revision: str | Sequence[str] | None = "b43fd2848298"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite cannot ALTER COLUMN. Batch mode recreates the table, and
    # dropping the old one is safe because alembic's sqlite connections
    # leave FKs off by default.
    with op.batch_alter_table("images") as batch_op:
        batch_op.alter_column(
            "sha256", existing_type=sa.VARCHAR(length=64), nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.alter_column(
            "sha256", existing_type=sa.VARCHAR(length=64), nullable=True
        )
