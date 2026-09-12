import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin
from apps.api.src.models.enums import DependencyType

if TYPE_CHECKING:
    from apps.api.src.models.file import RepositoryFile


class CodeDependency(Base, UUIDMixin):
    __tablename__ = "code_dependencies"

    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_package: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType, name="dependency_type"),
        default=DependencyType.IMPORT,
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    source_file: Mapped["RepositoryFile"] = relationship(
        "RepositoryFile",
        foreign_keys=[source_file_id],
        back_populates="dependencies",
    )
    target_file: Mapped[Optional["RepositoryFile"]] = relationship(
        "RepositoryFile",
        foreign_keys=[target_file_id],
    )
