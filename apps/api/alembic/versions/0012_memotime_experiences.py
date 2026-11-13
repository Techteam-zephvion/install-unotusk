"""create memotime_experiences table and indexes

Revision ID: 0012_memotime_experiences
Revises: 0011_evokg_triplets
Create Date: 2026-11-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_memotime_experiences"
down_revision: str | Sequence[str] | None = "0011_evokg_triplets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")
    uuid_type = postgresql.UUID(as_uuid=True).with_variant(sa.CHAR(36), "sqlite")

    op.create_table(
        "memotime_experiences",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "repository_id",
            uuid_type,
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("intent_type", sa.String(length=50), nullable=False),
        sa.Column("target_entities", jsonb_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_outcome", jsonb_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_contradictory", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("contradiction_detail", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "ix_memotime_repo_branch",
        "memotime_experiences",
        ["repository_id", "branch"],
        unique=False,
    )
    op.create_index(
        "ix_memotime_lookup",
        "memotime_experiences",
        ["repository_id", "branch", "intent_type"],
        unique=False,
    )
    op.create_index(
        "ix_memotime_commit",
        "memotime_experiences",
        ["repository_id", "commit_sha"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memotime_commit", table_name="memotime_experiences")
    op.drop_index("ix_memotime_lookup", table_name="memotime_experiences")
    op.drop_index("ix_memotime_repo_branch", table_name="memotime_experiences")
    op.drop_table("memotime_experiences")
