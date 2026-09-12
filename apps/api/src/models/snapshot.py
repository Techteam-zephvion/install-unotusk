import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin
from apps.api.src.models.enums import SnapshotStatus

if TYPE_CHECKING:
    from apps.api.src.models.file import RepositoryFile
    from apps.api.src.models.repository import Repository


def utc_now() -> datetime:
    return datetime.now(UTC)


class RepositorySnapshot(Base, UUIDMixin):
    __tablename__ = "repository_snapshots"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    branch: Mapped[str] = mapped_column(
        String(100),
        default="main",
        nullable=False,
    )
    status: Mapped[SnapshotStatus] = mapped_column(
        Enum(SnapshotStatus, name="snapshot_status"),
        default=SnapshotStatus.QUEUED,
        nullable=False,
    )
    total_files: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    processed_files: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_files: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="snapshots")
    files: Mapped[list["RepositoryFile"]] = relationship(
        "RepositoryFile",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
