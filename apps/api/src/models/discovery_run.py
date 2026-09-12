import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import DiscoveryJobStatus

if TYPE_CHECKING:
    from apps.api.src.models.finding import Finding
    from apps.api.src.models.project import Project
    from apps.api.src.models.snapshot import RepositorySnapshot


class DiscoveryRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "discovery_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[DiscoveryJobStatus] = mapped_column(
        String(50),
        nullable=False,
        default=DiscoveryJobStatus.QUEUED,
        index=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    findings_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="discovery_runs")
    snapshot: Mapped["RepositorySnapshot"] = relationship("RepositorySnapshot")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding",
        back_populates="discovery_run",
        cascade="all, delete-orphan",
    )
