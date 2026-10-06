"""add port to project

Revision ID: 0007_add_port_to_project
Revises: 0006_stage_5_project_knowledge
Create Date: 2026-10-01 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0007_add_port_to_project'
down_revision: str | Sequence[str] | None = '0006_stage_5_project_knowledge'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('port', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'port')
