"""add project memberships table

Revision ID: 0008_project_membership
Revises: 0007_add_port_to_project
Create Date: 2026-10-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_project_membership"
down_revision: str | Sequence[str] | None = "0007_add_port_to_project"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    membership_role_enum = sa.Enum("OWNER", "ADMIN", "MEMBER", name="membership_role", create_type=False)

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            membership_role_enum,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )
    op.create_index(
        op.f("ix_project_memberships_project_id"),
        "project_memberships",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_memberships_user_id"),
        "project_memberships",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_project_memberships_user_id"), table_name="project_memberships")
    op.drop_index(op.f("ix_project_memberships_project_id"), table_name="project_memberships")
    op.drop_table("project_memberships")
