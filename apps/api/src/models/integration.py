import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import IntegrationProvider, IntegrationStatus

if TYPE_CHECKING:
    from apps.api.src.models.project import Project


class Integration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "integrations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider"),
        default=IntegrationProvider.GITHUB,
        nullable=False,
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status"),
        default=IntegrationStatus.PENDING,
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Using JSONB on postgres; fallback to JSON if needed
    integration_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="integrations",
    )
