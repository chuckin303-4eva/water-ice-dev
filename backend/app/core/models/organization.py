from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Organization(Base):
    """A customer/tenant. See docs/DATABASE.md."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Validation workflow (ADR-0014). Defaults False so every existing
    # organization keeps today's behavior (member writes apply
    # immediately, same as admin writes) unless an admin opts in --
    # never a silent, retroactive behavior change.
    require_review_for_submissions: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
