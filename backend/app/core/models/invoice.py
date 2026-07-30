from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models.base import Base


class Invoice(Base):
    """Append-only billing history (ADR-0019) -- one row per charge
    event (subscribe, plan switch). `plan_slug`/`amount_cents` are
    snapshotted at issue time rather than joined live from the plan
    catalog, so a later catalog/price change never rewrites what a past
    invoice says was actually charged.
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True, nullable=False)
    plan_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="paid", nullable=False)
    provider_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
