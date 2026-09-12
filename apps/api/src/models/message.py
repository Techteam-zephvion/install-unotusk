import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    from apps.api.src.models.conversation import Conversation


def utc_now() -> datetime:
    return datetime.now(UTC)


class Message(Base, UUIDMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # "user", "assistant", "system"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    related_entities: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    confidence: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,  # "HIGH", "MEDIUM", "LOW"
    )
    debug_signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
