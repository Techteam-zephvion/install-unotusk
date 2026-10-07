"""add service ontology table and link to repositories

Revision ID: 0009_service_ontology
Revises: 0008_project_membership
Create Date: 2026-10-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009_service_ontology"
down_revision: str | Sequence[str] | None = "0008_project_membership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")

    op.create_table(
        "services",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tier", sa.String(length=50), nullable=True),
        sa.Column("service_metadata", jsonb_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_project_service_slug"),
    )
    op.create_index(
        op.f("ix_services_project_id"),
        "services",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_services_slug"),
        "services",
        ["slug"],
        unique=False,
    )

    op.add_column(
        "repositories",
        sa.Column("service_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_repositories_service_id_services",
        "repositories",
        "services",
        ["service_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_repositories_service_id"),
        "repositories",
        ["service_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_repositories_service_id"), table_name="repositories")
    op.drop_constraint("fk_repositories_service_id_services", "repositories", type_="foreignkey")
    op.drop_column("repositories", "service_id")

    op.drop_index(op.f("ix_services_slug"), table_name="services")
    op.drop_index(op.f("ix_services_project_id"), table_name="services")
    op.drop_table("services")
