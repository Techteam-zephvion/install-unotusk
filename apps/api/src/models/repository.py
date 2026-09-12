import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import IntegrationProvider

if TYPE_CHECKING:
    from apps.api.src.models.integration import Integration
    from apps.api.src.models.project import Project
    from apps.api.src.models.snapshot import RepositorySnapshot


class Repository(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "repositories"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider"),
        default=IntegrationProvider.GITHUB,
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
    )
    url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    repo_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="repositories")
    integration: Mapped["Integration"] = relationship("Integration")
    snapshots: Mapped[list["RepositorySnapshot"]] = relationship(
        "RepositorySnapshot",
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="desc(RepositorySnapshot.created_at)",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_project_repo_external"),
    )
