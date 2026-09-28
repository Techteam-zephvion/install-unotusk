import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from apps.api.src.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.file import RepositoryFile
    from apps.api.src.models.snapshot import RepositorySnapshot
    from apps.api.src.models.symbol import CodeSymbol

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:
    Vector = None  # type: ignore[assignment]
    _HAS_PGVECTOR = False


class CompatibleVector(TypeDecorator):
    """Compatible vector type that maps to Vector(1536) on PostgreSQL with pgvector,
    or falls back cleanly to JSONB or JSON when pgvector is absent."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and _HAS_PGVECTOR and Vector is not None:
            return dialect.type_descriptor(Vector(1536))
        elif dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        else:
            from sqlalchemy import JSON

            return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list | tuple):
            return [float(x) for x in value]
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, str):
            import json

            try:
                return json.loads(value)
            except Exception:
                cleaned = value.strip("[]")
                return [float(x.strip()) for x in cleaned.split(",") if x.strip()]
        if isinstance(value, list | tuple):
            return [float(x) for x in value]
        return value


def utc_now() -> datetime:
    return datetime.now(UTC)


class CodeChunk(Base, UUIDMixin):
    __tablename__ = "code_chunks"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_symbols.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
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
    embedding: Mapped[list[float] | None] = mapped_column(
        CompatibleVector,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    snapshot: Mapped["RepositorySnapshot"] = relationship("RepositorySnapshot")
    file: Mapped["RepositoryFile"] = relationship("RepositoryFile")
    symbol: Mapped["CodeSymbol | None"] = relationship("CodeSymbol")
