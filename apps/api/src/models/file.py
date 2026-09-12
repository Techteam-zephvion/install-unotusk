import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.dependency import CodeDependency
    from apps.api.src.models.snapshot import RepositorySnapshot
    from apps.api.src.models.symbol import CodeSymbol


class RepositoryFile(Base, UUIDMixin):
    __tablename__ = "repository_files"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    extension: Mapped[str] = mapped_column(
        String(50),
        default="",
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(100),
        default="UNKNOWN",
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_binary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_test: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    line_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    parser_supported: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    snapshot: Mapped["RepositorySnapshot"] = relationship("RepositorySnapshot", back_populates="files")
    symbols: Mapped[list["CodeSymbol"]] = relationship(
        "CodeSymbol",
        back_populates="file",
        cascade="all, delete-orphan",
    )
    dependencies: Mapped[list["CodeDependency"]] = relationship(
        "CodeDependency",
        foreign_keys="[CodeDependency.source_file_id]",
        back_populates="source_file",
        cascade="all, delete-orphan",
    )
