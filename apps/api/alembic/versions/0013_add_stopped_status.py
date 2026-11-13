"""add STOPPED to project_status enum

Revision ID: 0013_add_stopped_status
Revises: 0012_memotime_experiences
Create Date: 2026-11-13 16:57:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_add_stopped_status"
down_revision: str | Sequence[str] | None = "0012_memotime_experiences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add 'STOPPED' to project_status PostgreSQL enum if it does not exist
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'STOPPED';")


def downgrade() -> None:
    # PostgreSQL does not easily support removing enum values in-place; no-op
    pass

