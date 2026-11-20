"""automated hnsw vector index tuning on postgres code_chunks

Revision ID: 0015_hnsw_vector_index
Revises: 0014_conversation_archived_pinned
Create Date: 2026-11-20 23:45:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015_hnsw_vector_index"
down_revision: str | Sequence[str] | None = "0014_conversation_archived_pinned"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Gracefully create HNSW vector index with m=16, ef_construction=64 if pgvector extension is present
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'code_chunks') THEN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'code_chunks' AND column_name = 'embedding' AND data_type = 'USER-DEFINED'
                    ) THEN
                        CREATE INDEX IF NOT EXISTS ix_code_chunks_embedding_hnsw
                        ON code_chunks USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64);
                    END IF;
                END IF;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_embedding_hnsw;")
