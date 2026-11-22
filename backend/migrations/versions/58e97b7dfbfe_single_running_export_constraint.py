"""single running export constraint

Revision ID: 58e97b7dfbfe
Revises: 7c6b5862d2a0
Create Date: 2026-11-22 18:29:11.144811

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58e97b7dfbfe"
down_revision: str | Sequence[str] | None = "7c6b5862d2a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # expression-based: autogenerate can't produce or compare it, so it
    # is written by hand and mirrors models.Export.__table_args__
    op.create_index(
        "uq_exports_single_running",
        "exports",
        [sa.text("1")],
        unique=True,
        sqlite_where=sa.text("finished_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_exports_single_running", table_name="exports")
