import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import ReportStatus

if TYPE_CHECKING:
    from apps.api.src.models.discovery_run import DiscoveryRun
    from apps.api.src.models.project import Project
    from apps.api.src.models.snapshot import RepositorySnapshot


class ProjectIntelligenceReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_intelligence_reports"

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
    discovery_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discovery_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[ReportStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReportStatus.QUEUED,
        index=True,
    )
    report_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    report_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="reports")
    snapshot: Mapped["RepositorySnapshot"] = relationship("RepositorySnapshot")
    discovery_run: Mapped["DiscoveryRun | None"] = relationship("DiscoveryRun")

    __table_args__ = (
        Index("ix_project_intelligence_reports_project_created", "project_id", "created_at"),
    )
