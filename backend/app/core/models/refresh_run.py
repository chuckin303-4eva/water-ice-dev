from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class RefreshRun(Base):
    """One row per "Refresh Market" invocation (ADR-0004, implemented in
    ADR-0020). A run never writes to `locations` directly -- it only
    creates `validation_queue` entries; this table just tracks what a
    given invocation did, not the changes themselves.
    """

    __tablename__ = "refresh_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    triggered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    locations_reviewed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    changes_queued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    providers_used: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
