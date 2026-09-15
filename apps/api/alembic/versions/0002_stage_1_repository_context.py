"""Stage 1: repositories, repository_snapshots, repository_files, code_symbols, code_dependencies

Revision ID: 0002_stage_1_repository_context
Revises: 0001_initial_schema
Create Date: 2026-09-12 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_stage_1_repository_context"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create repositories table
    op.create_table(
        "repositories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("integration_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM("GITHUB", name="integration_provider", create_type=False),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column(
            "repo_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "external_id", name="uq_project_repo_external"),
    )
    op.create_index(
        op.f("ix_repositories_project_id"), "repositories", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_repositories_external_id"), "repositories", ["external_id"], unique=False
    )
    op.create_index(
        op.f("ix_repositories_integration_id"), "repositories", ["integration_id"], unique=False
    )

    # 2. Create repository_snapshots table
    op.create_table(
        "repository_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
        sa.Column("branch", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "CLONING",
                "SCANNING",
                "PARSING",
                "INDEXING",
                "COMPLETED",
                "FAILED",
                name="snapshot_status",
            ),
            nullable=False,
        ),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("processed_files", sa.Integer(), nullable=False),
        sa.Column("failed_files", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repository_snapshots_repository_id"),
        "repository_snapshots",
        ["repository_id"],
        unique=False,
    )

    # 3. Create repository_files table
    op.create_table(
        "repository_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("path", sa.String(length=1000), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_binary", sa.Boolean(), nullable=False),
        sa.Column("is_generated", sa.Boolean(), nullable=False),
        sa.Column("is_test", sa.Boolean(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("parser_supported", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["repository_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repository_files_snapshot_id"), "repository_files", ["snapshot_id"], unique=False
    )
    op.create_index(op.f("ix_repository_files_path"), "repository_files", ["path"], unique=False)

    # 4. Create code_symbols table
    op.create_table(
        "code_symbols",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("file_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "symbol_type",
            sa.Enum(
                "CLASS",
                "FUNCTION",
                "METHOD",
                "INTERFACE",
                "TYPE",
                "ENUM",
                "MODULE",
                name="symbol_type",
            ),
            nullable=False,
        ),
        sa.Column("qualified_name", sa.String(length=500), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("parent_symbol_id", sa.UUID(), nullable=True),
        sa.Column(
            "symbol_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_symbol_id"], ["code_symbols.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_symbols_file_id"), "code_symbols", ["file_id"], unique=False)
    op.create_index(op.f("ix_code_symbols_name"), "code_symbols", ["name"], unique=False)

    # 5. Create code_dependencies table
    op.create_table(
        "code_dependencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_file_id", sa.UUID(), nullable=False),
        sa.Column("target_file_id", sa.UUID(), nullable=True),
        sa.Column("external_package", sa.String(length=255), nullable=True),
        sa.Column(
            "dependency_type",
            sa.Enum("IMPORT", "REQUIRE", "FROM_IMPORT", name="dependency_type"),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_file_id"], ["repository_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_code_dependencies_source_file_id"),
        "code_dependencies",
        ["source_file_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_code_dependencies_target_file_id"),
        "code_dependencies",
        ["target_file_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_code_dependencies_external_package"),
        "code_dependencies",
        ["external_package"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("code_dependencies")
    op.execute("DROP TYPE IF EXISTS dependency_type;")

    op.drop_table("code_symbols")
    op.execute("DROP TYPE IF EXISTS symbol_type;")

    op.drop_table("repository_files")
    op.drop_table("repository_snapshots")
    op.execute("DROP TYPE IF EXISTS snapshot_status;")

    op.drop_table("repositories")
