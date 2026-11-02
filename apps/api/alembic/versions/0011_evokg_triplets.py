"""create evokg_triplets table and temporal indexes

Revision ID: 0011_evokg_triplets
Revises: 0010_code_chunk_atom_metadata
Create Date: 2026-11-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_evokg_triplets"
down_revision: str | Sequence[str] | None = "0010_code_chunk_atom_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")
    uuid_type = postgresql.UUID(as_uuid=True).with_variant(sa.CHAR(36), "sqlite")

    op.create_table(
        "evokg_triplets",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "repository_id",
            uuid_type,
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            uuid_type,
            sa.ForeignKey("repository_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("subject_id", sa.String(length=500), nullable=False),
        sa.Column("relation", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.String(length=500), nullable=False),
        sa.Column(
            "file_id",
            uuid_type,
            sa.ForeignKey("repository_files.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "symbol_id",
            uuid_type,
            sa.ForeignKey("code_symbols.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_exclusive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scope_key", sa.String(length=255), nullable=False, server_default="default"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column(
            "superseded_by_id",
            uuid_type,
            sa.ForeignKey("evokg_triplets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "supersedes_id",
            uuid_type,
            sa.ForeignKey("evokg_triplets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("confidence_level", sa.String(length=20), nullable=False, server_default="UNCERTAIN"),
        sa.Column("is_uncertain", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("has_temporal_conflict", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("conflict_detail", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("symbol_name", sa.String(length=255), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provenance", jsonb_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 1. Active outgoing relationships: (repository_id, branch, subject_id, relation)
    op.create_index(
        "ix_evokg_active_outgoing",
        "evokg_triplets",
        ["repository_id", "branch", "subject_id", "relation"],
        unique=False,
    )

    # 2. Active incoming relationships: (repository_id, branch, object_id, relation)
    op.create_index(
        "ix_evokg_active_incoming",
        "evokg_triplets",
        ["repository_id", "branch", "object_id", "relation"],
        unique=False,
    )

    # 3. Temporal lookup: (repository_id, branch, subject_id, valid_from, valid_to)
    op.create_index(
        "ix_evokg_temporal_lookup",
        "evokg_triplets",
        ["repository_id", "branch", "subject_id", "valid_from", "valid_to"],
        unique=False,
    )

    # 4. Exclusive conflict detection: (repository_id, branch, subject_id, relation, scope_key)
    op.create_index(
        "ix_evokg_exclusive_conflict",
        "evokg_triplets",
        ["repository_id", "branch", "subject_id", "relation", "scope_key"],
        unique=False,
    )

    # 5. Snapshot and commit lookup
    op.create_index(
        "ix_evokg_snapshot",
        "evokg_triplets",
        ["repository_id", "snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_evokg_commit",
        "evokg_triplets",
        ["repository_id", "commit_sha"],
        unique=False,
    )

    # 6. Fingerprint-based idempotency
    op.create_index(
        "ix_evokg_repo_fingerprint",
        "evokg_triplets",
        ["repository_id", "fingerprint"],
        unique=False,
    )

    # 7. Partial unique index on PostgreSQL: duplicate protection against multiple active exclusive assertions
    op.create_index(
        "uq_evokg_active_exclusive",
        "evokg_triplets",
        ["repository_id", "branch", "subject_id", "relation", "scope_key"],
        unique=True,
        postgresql_where=sa.text(
            "is_exclusive = true AND valid_to IS NULL AND is_uncertain = false AND has_temporal_conflict = false"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_evokg_active_exclusive", table_name="evokg_triplets")
    op.drop_index("ix_evokg_repo_fingerprint", table_name="evokg_triplets")
    op.drop_index("ix_evokg_commit", table_name="evokg_triplets")
    op.drop_index("ix_evokg_snapshot", table_name="evokg_triplets")
    op.drop_index("ix_evokg_exclusive_conflict", table_name="evokg_triplets")
    op.drop_index("ix_evokg_temporal_lookup", table_name="evokg_triplets")
    op.drop_index("ix_evokg_active_incoming", table_name="evokg_triplets")
    op.drop_index("ix_evokg_active_outgoing", table_name="evokg_triplets")
    op.drop_table("evokg_triplets")
