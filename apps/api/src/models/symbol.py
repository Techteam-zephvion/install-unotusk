import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin
from apps.api.src.models.enums import SymbolType

if TYPE_CHECKING:
    from apps.api.src.models.file import RepositoryFile


class CodeSymbol(Base, UUIDMixin):
    __tablename__ = "code_symbols"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    symbol_type: Mapped[SymbolType] = mapped_column(
        Enum(SymbolType, name="symbol_type"),
        nullable=False,
    )
    qualified_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    start_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    end_line: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    file: Mapped["RepositoryFile"] = relationship("RepositoryFile", back_populates="symbols")
