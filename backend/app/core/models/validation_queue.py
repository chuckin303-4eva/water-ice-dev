from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class ValidationQueue(Base):
    """Designed in ADR-0003, implemented in ADR-0014 (Phase 2, validation
    workflow). Records awaiting human review before their data is
    trusted.

    `entity_id` is nullable, extending the original design: a proposed
    *create* has no entity yet (nothing to point at until approved), so
    `entity_type = "location"` with `entity_id = NULL` means "propose a
    new location"; `entity_type = "location"` with `entity_id` set means
    "propose changes to this existing location." `proposed_changes`
    holds the full create payload or just the changed fields,
    respectively.
    """

    __tablename__ = "validation_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    proposed_changes: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
