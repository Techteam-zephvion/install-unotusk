import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)

if TYPE_CHECKING:
    from apps.api.src.models.discovery_run import DiscoveryRun
    from apps.api.src.models.project import Project
    from apps.api.src.models.snapshot import RepositorySnapshot


class Finding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "findings"

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

    category: Mapped[FindingCategory] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    why_it_matters: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    confidence: Mapped[FindingConfidence] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[FindingStatus] = mapped_column(
        String(50),
        nullable=False,
        default=FindingStatus.OPEN,
        index=True,
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Structured evidence: list of dicts with file, symbol, lines, relationship, snippet, metrics
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # Related symbols, files, components
    related_entities: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    finding_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="findings")
    snapshot: Mapped["RepositorySnapshot"] = relationship("RepositorySnapshot")
    discovery_run: Mapped["DiscoveryRun | None"] = relationship("DiscoveryRun", back_populates="findings")

    __table_args__ = (
        Index("ix_findings_project_status", "project_id", "status"),
        Index("ix_findings_project_severity", "project_id", "severity"),
        Index("ix_findings_project_category", "project_id", "category"),
    )
