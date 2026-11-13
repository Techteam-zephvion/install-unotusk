import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.repository import Repository


def utc_now() -> datetime:
    return datetime.now(UTC)


class MemoTimeExperience(Base, UUIDMixin, TimestampMixin):
    """
    MemoTime Persistent Experience Memory Model (arXiv:2510.13614 §3.2-3.4).
    Stores verified reasoning traces, temporal bounds, and cross-question-type
    historical/diff/evolution evidence scoped to a repository and branch.
    """

    __tablename__ = "memotime_experiences"

    # Repository & Branch Isolation Scope
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
        index=True,
    )

    # Query & Intent Classification
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    intent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Target Entities (Symbols, File Paths, Modules)
    target_entities: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Provenance & Temporal Anchors
    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        index=True,
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Verified Reasoning Outcome & Diff/Trace Payload
    # E.g. {"line_spans": [...], "added_lines": [...], "deleted_lines": [...], "verified_facts": [...], "strategy": "DIFF"}
    verified_outcome: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Verification & Quality Gate (Must be >= 0.80 confidence, non-contradictory)
    confidence_score: Mapped[float] = mapped_column(
        Float,
        default=0.85,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_contradictory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    contradiction_detail: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Attribution & Explainability
    attribution: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_memotime_repo_branch",
            "repository_id",
            "branch",
        ),
        Index(
            "ix_memotime_lookup",
            "repository_id",
            "branch",
            "intent_type",
        ),
        Index(
            "ix_memotime_commit",
            "repository_id",
            "commit_sha",
        ),
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")
