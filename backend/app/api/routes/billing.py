from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.schemas.billing import (
    InvoiceResponse,
    PlanResponse,
    SubscribeRequest,
    SubscriptionResponse,
)
from app.core.models.user import User
from app.db.session import get_db
from app.services import billing_service
from app.services.plan_catalog import list_plans

router = APIRouter(prefix="/billing", tags=["billing"])


def _plan_response(plan) -> PlanResponse:
    return PlanResponse(slug=plan.slug, name=plan.name, price_cents=plan.price_cents, features=plan.features)


def _subscription_response(db: Session, organization_id: int) -> SubscriptionResponse:
    plan = billing_service.get_effective_plan(db, organization_id)
    subscription = billing_service.get_subscription(db, organization_id)
    if subscription is not None and subscription.status == "active":
        return SubscriptionResponse(
            plan=_plan_response(plan),
            status="active",
            provider=subscription.provider,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
        )
    return SubscriptionResponse(
        plan=_plan_response(plan),
        status="active",
        provider="none",
        current_period_start=None,
        current_period_end=None,
    )


@router.get("/plans", response_model=list[PlanResponse])
def get_plans(current_user: User = Depends(get_current_user)) -> list[PlanResponse]:
    return [_plan_response(p) for p in list_plans()]


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Any authenticated member can see their org's current plan --
    only subscribing/canceling is admin-gated (same split as
    organization settings, ADR-0014)."""
    return _subscription_response(db, current_user.organization_id)


@router.post("/subscribe", response_model=SubscriptionResponse)
def subscribe(
    body: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SubscriptionResponse:
    try:
        billing_service.subscribe(db, current_user.organization_id, body.plan_slug)
    except billing_service.PlanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except billing_service.CannotSubscribeToFreeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _subscription_response(db, current_user.organization_id)


@router.post("/cancel", response_model=SubscriptionResponse)
def cancel(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SubscriptionResponse:
    try:
        billing_service.cancel_subscription(db, current_user.organization_id)
    except billing_service.NoActiveSubscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _subscription_response(db, current_user.organization_id)


@router.get("/invoices", response_model=list[InvoiceResponse])
def get_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[InvoiceResponse]:
    """Admin-only, unlike /subscription -- billing history is financial
    data, treated as more sensitive than a plain status readout."""
    return [
        InvoiceResponse.model_validate(inv)
        for inv in billing_service.list_invoices(db, current_user.organization_id)
    ]
