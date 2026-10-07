import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.project import Project
    from apps.api.src.models.repository import Repository


class Service(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "services"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    tier: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="tier-1",
    )
    service_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="services")
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository",
        back_populates="service",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_project_service_slug"),
    )
