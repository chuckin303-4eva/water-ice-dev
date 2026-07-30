from datetime import datetime

from pydantic import BaseModel


class PlanResponse(BaseModel):
    slug: str
    name: str
    price_cents: int
    features: list[str]


class SubscriptionResponse(BaseModel):
    plan: PlanResponse
    status: str
    provider: str
    current_period_start: datetime | None
    current_period_end: datetime | None


class InvoiceResponse(BaseModel):
    id: int
    plan_slug: str
    amount_cents: int
    currency: str
    status: str
    period_start: datetime
    period_end: datetime
    issued_at: datetime

    model_config = {"from_attributes": True}


class SubscribeRequest(BaseModel):
    plan_slug: str
