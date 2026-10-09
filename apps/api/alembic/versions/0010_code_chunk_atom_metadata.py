"""add atom metadata fields to code_chunks

Revision ID: 0010_code_chunk_atom_metadata
Revises: 0009_service_ontology
Create Date: 2026-10-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010_code_chunk_atom_metadata"
down_revision: str | Sequence[str] | None = "0009_service_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")

    op.add_column("code_chunks", sa.Column("commit_sha", sa.String(length=40), nullable=True))
    op.add_column("code_chunks", sa.Column("commit_message", sa.Text(), nullable=True))
    op.add_column("code_chunks", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.add_column("code_chunks", sa.Column("provenance", jsonb_type, nullable=True))

    op.create_index(
        op.f("ix_code_chunks_fingerprint"),
        "code_chunks",
        ["fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_code_chunks_commit_sha"),
        "code_chunks",
        ["commit_sha"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_code_chunks_commit_sha"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_fingerprint"), table_name="code_chunks")
    op.drop_column("code_chunks", "provenance")
    op.drop_column("code_chunks", "fingerprint")
    op.drop_column("code_chunks", "commit_message")
    op.drop_column("code_chunks", "commit_sha")
