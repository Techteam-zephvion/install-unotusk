"""Stage 4: project_intelligence_reports

Revision ID: 0005_stage_4_reports
Revises: 0004_stage_3_discovery
Create Date: 2026-09-12 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_stage_4_reports"
down_revision: str | None = "0004_stage_3_discovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_intelligence_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("discovery_run_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="QUEUED"),
        sa.Column("report_version", sa.String(length=50), nullable=False, server_default="1.0.0"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "report_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_intelligence_reports_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["repository_snapshots.id"],
            name=op.f("fk_project_intelligence_reports_snapshot_id_repository_snapshots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["discovery_run_id"],
            ["discovery_runs.id"],
            name=op.f("fk_project_intelligence_reports_discovery_run_id_discovery_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_intelligence_reports")),
    )

    op.create_index(
        op.f("ix_project_intelligence_reports_project_id"),
        "project_intelligence_reports",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_intelligence_reports_snapshot_id"),
        "project_intelligence_reports",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_intelligence_reports_discovery_run_id"),
        "project_intelligence_reports",
        ["discovery_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_intelligence_reports_status"),
        "project_intelligence_reports",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_project_intelligence_reports_project_created",
        "project_intelligence_reports",
        ["project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_intelligence_reports_project_created", table_name="project_intelligence_reports"
    )
    op.drop_index(
        op.f("ix_project_intelligence_reports_status"), table_name="project_intelligence_reports"
    )
    op.drop_index(
        op.f("ix_project_intelligence_reports_discovery_run_id"),
        table_name="project_intelligence_reports",
    )
    op.drop_index(
        op.f("ix_project_intelligence_reports_snapshot_id"),
        table_name="project_intelligence_reports",
    )
    op.drop_index(
        op.f("ix_project_intelligence_reports_project_id"),
        table_name="project_intelligence_reports",
    )
    op.drop_table("project_intelligence_reports")
