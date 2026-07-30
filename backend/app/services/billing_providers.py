"""Billing provider interface (Phase 3 "Subscriptions"/"Billing";
ADR-0019) -- same replaceable-module shape as the Market Refresh
Engine's `MarketDataProvider` (ADR-0004), so a real payment processor
can be swapped in later without touching subscribe/cancel/invoice logic.

Only `MockBillingProvider` exists today: it simulates a processor
entirely in-process, collects no real payment method, and every action
succeeds immediately. Adding a real provider (Stripe or otherwise) is a
new ADR plus explicit sign-off before it's wired in as the active
provider -- same paid-integration gating precedent as ADR-0004, not a
silent addition.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple, Protocol

from app.services.plan_catalog import Plan

_BILLING_PERIOD_DAYS = 30


class ProviderSubscriptionResult(NamedTuple):
    provider_subscription_id: str
    period_start: datetime
    period_end: datetime


class BillingProvider(Protocol):
    slug: str

    def create_subscription(self, organization_id: int, plan: Plan) -> ProviderSubscriptionResult: ...

    def cancel_subscription(self, provider_subscription_id: str) -> None: ...


class MockBillingProvider:
    """No real payment method is ever collected -- not even a fake
    credit-card form -- consistent with this project's pattern of never
    faking something that isn't actually built (e.g. the disclosed "no
    email service" gaps elsewhere). A visible banner in the billing UI
    states this plainly to whoever's testing it.
    """

    slug = "mock"

    def create_subscription(self, organization_id: int, plan: Plan) -> ProviderSubscriptionResult:
        now = datetime.now(UTC)
        return ProviderSubscriptionResult(
            provider_subscription_id=f"mock_sub_{uuid.uuid4()}",
            period_start=now,
            period_end=now + timedelta(days=_BILLING_PERIOD_DAYS),
        )

    def cancel_subscription(self, provider_subscription_id: str) -> None:
        pass  # nothing external to cancel


def get_active_provider() -> BillingProvider:
    return MockBillingProvider()
