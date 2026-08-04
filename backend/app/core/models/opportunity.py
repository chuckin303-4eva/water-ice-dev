import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Opportunity(Base):
    """The human pursuit-workflow layer on top of a location's computed
    `opportunity_score` (ADR-0009) -- tracks who is actually pursuing a
    given location and how far along they are, kept separate so "how good
    is this site, generically" never gets conflated with "what's the
    status of our specific pursuit of it." Designed in ADR-0003 alongside
    the rest of the schema but never actually built until now (ADR-0021)
    -- it fell through Phase 1/2/3 without ever being a numbered roadmap
    item, unlike host_businesses/brands/photos which had the same gap.

    Org-scoped (unlike `locations` itself, ADR-0002): the same location can
    be pursued independently by more than one organization.
    """

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"), index=True, nullable=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=False
    )
    stage: Mapped[str] = mapped_column(String(20), default="identified", nullable=False)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
