"""Subscription/invoice orchestration (Phase 3; ADR-0019).

An organization with no `subscriptions` row is on the free plan --
absence of a row is the default state, never an error, same convention
used for `require_review_for_submissions` (ADR-0014) and other opt-in
flags in this schema. Cancellation is immediate for v1 (not
at-period-end), which needs no background job or lazy-expiry check to
prove the core flow -- see ADR-0019 for the tradeoff.
"""

from sqlalchemy.orm import Session

from app.core.models.invoice import Invoice
from app.core.models.subscription import Subscription
from app.services import billing_providers
from app.services.plan_catalog import FREE_PLAN_SLUG, Plan, get_plan


class PlanNotFoundError(Exception):
    pass


class CannotSubscribeToFreeError(Exception):
    pass


class NoActiveSubscriptionError(Exception):
    pass


def get_subscription(db: Session, organization_id: int) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.organization_id == organization_id).first()


def get_effective_plan(db: Session, organization_id: int) -> Plan:
    subscription = get_subscription(db, organization_id)
    if subscription is None or subscription.status != "active":
        return get_plan(FREE_PLAN_SLUG)
    plan = get_plan(subscription.plan_slug)
    return plan if plan is not None else get_plan(FREE_PLAN_SLUG)


def subscribe(db: Session, organization_id: int, plan_slug: str) -> Subscription:
    if plan_slug == FREE_PLAN_SLUG:
        raise CannotSubscribeToFreeError("Use cancel to return to the free plan, not subscribe")
    plan = get_plan(plan_slug)
    if plan is None:
        raise PlanNotFoundError(f"Unknown plan: {plan_slug}")

    provider = billing_providers.get_active_provider()
    result = provider.create_subscription(organization_id, plan)

    subscription = get_subscription(db, organization_id)
    if subscription is None:
        subscription = Subscription(organization_id=organization_id)
        db.add(subscription)

    subscription.plan_slug = plan.slug
    subscription.status = "active"
    subscription.provider = provider.slug
    subscription.provider_subscription_id = result.provider_subscription_id
    subscription.current_period_start = result.period_start
    subscription.current_period_end = result.period_end
    db.commit()
    db.refresh(subscription)

    # No proration on a plan switch for v1 -- always a full-price invoice
    # for the newly selected plan (see ADR-0019).
    db.add(
        Invoice(
            organization_id=organization_id,
            subscription_id=subscription.id,
            plan_slug=plan.slug,
            amount_cents=plan.price_cents,
            status="paid",
            provider_invoice_id=f"mock_inv_{subscription.provider_subscription_id}",
            period_start=result.period_start,
            period_end=result.period_end,
        )
    )
    db.commit()
    return subscription


def cancel_subscription(db: Session, organization_id: int) -> Subscription:
    subscription = get_subscription(db, organization_id)
    if subscription is None or subscription.status != "active":
        raise NoActiveSubscriptionError("This organization has no active paid subscription to cancel")

    provider = billing_providers.get_active_provider()
    if subscription.provider_subscription_id:
        provider.cancel_subscription(subscription.provider_subscription_id)

    subscription.status = "canceled"
    db.commit()
    db.refresh(subscription)
    return subscription


def list_invoices(db: Session, organization_id: int) -> list[Invoice]:
    return (
        db.query(Invoice)
        .filter(Invoice.organization_id == organization_id)
        .order_by(Invoice.issued_at.desc())
        .all()
    )
