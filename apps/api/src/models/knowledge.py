import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import KnowledgeCategory, KnowledgeStatus

if TYPE_CHECKING:
    from apps.api.src.models.finding import Finding
    from apps.api.src.models.project import Project
    from apps.api.src.models.user import User


class ProjectKnowledge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_knowledge"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category: Mapped[KnowledgeCategory] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[KnowledgeStatus] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeStatus.ACTIVE,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CUSTOMER",
    )
    source_reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    source_reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    related_file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
    )
    related_symbol: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    related_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    related_entity_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    knowledge_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="knowledge_items")
    creator: Mapped["User | None"] = relationship("User")
    related_finding: Mapped["Finding | None"] = relationship("Finding")

    __table_args__ = (
        Index("ix_project_knowledge_project_status", "project_id", "status"),
        Index("ix_project_knowledge_project_created", "project_id", "created_at"),
    )
