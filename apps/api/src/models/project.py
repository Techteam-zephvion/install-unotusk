import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, TimestampMixin, UUIDMixin
from apps.api.src.models.enums import ProjectStatus

if TYPE_CHECKING:
    from apps.api.src.models.conversation import Conversation
    from apps.api.src.models.discovery_run import DiscoveryRun
    from apps.api.src.models.finding import Finding
    from apps.api.src.models.integration import Integration
    from apps.api.src.models.knowledge import ProjectKnowledge
    from apps.api.src.models.organization import Organization
    from apps.api.src.models.report import ProjectIntelligenceReport
    from apps.api.src.models.repository import Repository


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        default=ProjectStatus.CREATED,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects",
    )
    integrations: Mapped[list["Integration"]] = relationship(
        "Integration",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    findings: Mapped[list["Finding"]] = relationship(
        "Finding",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    discovery_runs: Mapped[list["DiscoveryRun"]] = relationship(
        "DiscoveryRun",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["ProjectIntelligenceReport"]] = relationship(
        "ProjectIntelligenceReport",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    knowledge_items: Mapped[list["ProjectKnowledge"]] = relationship(
        "ProjectKnowledge",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_org_project_slug"),
    )
