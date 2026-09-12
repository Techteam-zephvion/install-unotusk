"""Stage 5: project_knowledge

Revision ID: 0006_stage_5_project_knowledge
Revises: 0005_stage_4_reports
Create Date: 2026-09-12 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_stage_5_project_knowledge"
down_revision: str | None = "0005_stage_4_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_knowledge",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="CUSTOMER"),
        sa.Column("source_reference_type", sa.String(length=50), nullable=True),
        sa.Column("source_reference_id", sa.String(length=255), nullable=True),
        sa.Column("related_file_path", sa.String(length=500), nullable=True),
        sa.Column("related_symbol", sa.String(length=255), nullable=True),
        sa.Column("related_finding_id", sa.UUID(), nullable=True),
        sa.Column("related_entity_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_id", sa.String(length=255), nullable=True),
        sa.Column(
            "knowledge_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_knowledge_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_project_knowledge_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_finding_id"],
            ["findings.id"],
            name=op.f("fk_project_knowledge_related_finding_id_findings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_knowledge")),
    )

    op.create_index(
        op.f("ix_project_knowledge_project_id"),
        "project_knowledge",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_created_by"),
        "project_knowledge",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_category"),
        "project_knowledge",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_status"),
        "project_knowledge",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_related_file_path"),
        "project_knowledge",
        ["related_file_path"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_related_symbol"),
        "project_knowledge",
        ["related_symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_knowledge_related_finding_id"),
        "project_knowledge",
        ["related_finding_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_knowledge_project_status",
        "project_knowledge",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_project_knowledge_project_created",
        "project_knowledge",
        ["project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_knowledge_project_created", table_name="project_knowledge")
    op.drop_index("ix_project_knowledge_project_status", table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_related_finding_id"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_related_symbol"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_related_file_path"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_status"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_category"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_created_by"), table_name="project_knowledge")
    op.drop_index(op.f("ix_project_knowledge_project_id"), table_name="project_knowledge")
    op.drop_table("project_knowledge")
