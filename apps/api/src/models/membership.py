import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.src.db.base import Base, UUIDMixin
from apps.api.src.models.enums import MembershipRole

if TYPE_CHECKING:
    from apps.api.src.models.organization import Organization
    from apps.api.src.models.user import User


def utc_now() -> datetime:
    return datetime.now(UTC)


class OrganizationMembership(Base, UUIDMixin):
    __tablename__ = "organization_memberships"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role"),
        default=MembershipRole.MEMBER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
