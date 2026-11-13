import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.file import RepositoryFile
    from apps.api.src.models.repository import Repository
    from apps.api.src.models.snapshot import RepositorySnapshot
    from apps.api.src.models.symbol import CodeSymbol


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvoKGTriplet(Base, UUIDMixin, TimestampMixin):
    """
    EvoKG Persistent Temporal Triplet Model (arXiv:2509.15464 §3.1-3.2).
    Represents an evolving code relationship with validity interval [valid_from, valid_to),
    observation time, confidence calibration, branch isolation, and explicit supersession links.
    """

    __tablename__ = "evokg_triplets"

    # Repository & Branch Identity Scope
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
        index=True,
    )

    # Entity & Predicate Identity (Repository-scoped canonical identifiers)
    subject_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    relation: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    object_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    # Optional foreign keys to AST entities
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Classification & Exclusivity (T2.1 Taxonomy)
    is_exclusive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    scope_key: Mapped[str] = mapped_column(
        String(255),
        default="default",
        nullable=False,
    )

    # Temporal Intervals (Validity vs Observation time)
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    observation_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=True,
    )
    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )

    # Supersession DAG pointers
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evokg_triplets.id", ondelete="SET NULL"),
        nullable=True,
    )
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evokg_triplets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Confidence Calibration & Uncertainty
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.50,
        nullable=False,
    )
    confidence_level: Mapped[str] = mapped_column(
        String(20),
        default="UNCERTAIN",
        nullable=False,
    )
    is_uncertain: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    has_temporal_conflict: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    conflict_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Provenance
    file_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    symbol_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    line_start: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    line_end: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Table Indexes for active retrieval, temporal search, conflict detection, and idempotency
    __table_args__ = (
        Index(
            "ix_evokg_active_outgoing",
            "repository_id",
            "branch",
            "subject_id",
            "relation",
        ),
        Index(
            "ix_evokg_active_incoming",
            "repository_id",
            "branch",
            "object_id",
            "relation",
        ),
        Index(
            "ix_evokg_temporal_lookup",
            "repository_id",
            "branch",
            "subject_id",
            "valid_from",
            "valid_to",
        ),
        Index(
            "ix_evokg_exclusive_conflict",
            "repository_id",
            "branch",
            "subject_id",
            "relation",
            "scope_key",
        ),
        Index(
            "ix_evokg_snapshot",
            "repository_id",
            "snapshot_id",
        ),
        Index(
            "ix_evokg_commit",
            "repository_id",
            "commit_sha",
        ),
        Index(
            "ix_evokg_repo_fingerprint",
            "repository_id",
            "fingerprint",
        ),
        Index(
            "uq_evokg_active_exclusive",
            "repository_id",
            "branch",
            "subject_id",
            "relation",
            "scope_key",
            unique=True,
            postgresql_where=text(
                "is_exclusive = true AND valid_to IS NULL AND is_uncertain = false AND has_temporal_conflict = false"
            ),
            sqlite_where=text(
                "is_exclusive = 1 AND valid_to IS NULL AND is_uncertain = 0 AND has_temporal_conflict = 0"
            ),
        ),
    )

    # Model relationships
    repository: Mapped["Repository"] = relationship("Repository")
    snapshot: Mapped["RepositorySnapshot | None"] = relationship("RepositorySnapshot")
    file: Mapped["RepositoryFile | None"] = relationship("RepositoryFile")
    symbol: Mapped["CodeSymbol | None"] = relationship("CodeSymbol")
    superseded_by: Mapped["EvoKGTriplet | None"] = relationship(
        "EvoKGTriplet",
        foreign_keys=[superseded_by_id],
        remote_side="EvoKGTriplet.id",
        post_update=True,
    )
    supersedes: Mapped["EvoKGTriplet | None"] = relationship(
        "EvoKGTriplet",
        foreign_keys=[supersedes_id],
        remote_side="EvoKGTriplet.id",
        post_update=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("is_exclusive", False)
        kwargs.setdefault("scope_key", "default")
        kwargs.setdefault("confidence_score", 0.50)
        kwargs.setdefault("confidence_level", "UNCERTAIN")

        # Ensure confidence category and uncertainty flags remain consistent
        conf_level = kwargs.get("confidence_level", "UNCERTAIN")
        if conf_level == "UNCERTAIN":
            kwargs.setdefault("is_uncertain", True)
        elif conf_level in ("HIGH", "MEDIUM"):
            kwargs.setdefault("is_uncertain", False)
        else:
            # Unknown confidence categories must never default to HIGH
            kwargs["confidence_level"] = "UNCERTAIN"
            kwargs["is_uncertain"] = True

        # If uncertain is set, confidence category must not be HIGH
        if kwargs.get("is_uncertain", False):
            if kwargs["confidence_level"] == "HIGH":
                kwargs["confidence_level"] = "UNCERTAIN"
            if kwargs.get("confidence_score", 0.50) > 0.50:
                kwargs["confidence_score"] = 0.50

        kwargs.setdefault("is_uncertain", True)
        kwargs.setdefault("has_temporal_conflict", False)
        kwargs.setdefault("branch", "main")
        kwargs.setdefault("provenance", {})
        super().__init__(**kwargs)
