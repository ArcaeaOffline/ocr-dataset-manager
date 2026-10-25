"""images hidden flag

Revision ID: 5a45f765f8ae
Revises: 56664ad12089
Create Date: 2026-10-25 21:37:23.442103

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a45f765f8ae"
down_revision: str | Sequence[str] | None = "56664ad12089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "images",
        sa.Column("hidden", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("images", "hidden")
