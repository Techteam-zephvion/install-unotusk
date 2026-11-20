"""add is_archived and is_pinned to conversations table

Revision ID: 0014_conversation_archived_pinned
Revises: 0013_add_stopped_status
Create Date: 2026-11-20 16:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014_conversation_archived_pinned"
down_revision: str | Sequence[str] | None = "0013_add_stopped_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_archived and is_pinned columns to conversations table safely
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;"
    )
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversations_is_archived ON conversations (is_archived);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversations_is_pinned ON conversations (is_pinned);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_conversations_is_pinned;")
    op.execute("DROP INDEX IF EXISTS ix_conversations_is_archived;")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS is_pinned;")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS is_archived;")
