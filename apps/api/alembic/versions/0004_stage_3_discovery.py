"""Stage 3: discovery_runs, findings

Revision ID: 0004_stage_3_discovery
Revises: 0003_stage_2_intelligence
Create Date: 2026-09-12 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_stage_3_discovery"
down_revision: str | None = "0003_stage_2_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create discovery_runs table
    op.create_table(
        "discovery_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_discovery_runs_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["repository_snapshots.id"],
            name=op.f("fk_discovery_runs_snapshot_id_repository_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discovery_runs")),
    )
    op.create_index(
        op.f("ix_discovery_runs_project_id"),
        "discovery_runs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_runs_snapshot_id"),
        "discovery_runs",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_runs_status"),
        "discovery_runs",
        ["status"],
        unique=False,
    )

    # 2. Create findings table
    op.create_table(
        "findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("discovery_run_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "related_entities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "finding_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_findings_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["repository_snapshots.id"],
            name=op.f("fk_findings_snapshot_id_repository_snapshots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["discovery_run_id"],
            ["discovery_runs.id"],
            name=op.f("fk_findings_discovery_run_id_discovery_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_findings")),
    )
    op.create_index(
        op.f("ix_findings_project_id"),
        "findings",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_snapshot_id"),
        "findings",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_discovery_run_id"),
        "findings",
        ["discovery_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_category"),
        "findings",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_severity"),
        "findings",
        ["severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_findings_status"),
        "findings",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_findings_project_status",
        "findings",
        ["project_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_findings_project_severity",
        "findings",
        ["project_id", "severity"],
        unique=False,
    )
    op.create_index(
        "ix_findings_project_category",
        "findings",
        ["project_id", "category"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_findings_project_category", table_name="findings")
    op.drop_index("ix_findings_project_severity", table_name="findings")
    op.drop_index("ix_findings_project_status", table_name="findings")
    op.drop_index(op.f("ix_findings_status"), table_name="findings")
    op.drop_index(op.f("ix_findings_severity"), table_name="findings")
    op.drop_index(op.f("ix_findings_category"), table_name="findings")
    op.drop_index(op.f("ix_findings_discovery_run_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_snapshot_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_project_id"), table_name="findings")
    op.drop_table("findings")

    op.drop_index(op.f("ix_discovery_runs_status"), table_name="discovery_runs")
    op.drop_index(op.f("ix_discovery_runs_snapshot_id"), table_name="discovery_runs")
    op.drop_index(op.f("ix_discovery_runs_project_id"), table_name="discovery_runs")
    op.drop_table("discovery_runs")
