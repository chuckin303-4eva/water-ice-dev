"""Pricing plan catalog (Phase 3 "Subscriptions"; ADR-0019).

Deliberately not a database table. Pricing tiers are a business/deploy-
time decision, not user-editable data -- there's no admin UI anywhere
in this app for managing arbitrary reference data like this, and adding
one just to avoid a code change on the rare occasion pricing changes
would be pure premature flexibility. `subscriptions`/`invoices` reference
a plan by this fixed `slug`, not a foreign key.

Monthly billing only for v1 -- no annual/interval selection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    slug: str
    name: str
    price_cents: int
    features: list[str]


PLANS: list[Plan] = [
    Plan(
        slug="free",
        name="Free",
        price_cents=0,
        features=["Up to 25 locations", "Basic scoring", "Community support"],
    ),
    Plan(
        slug="starter",
        name="Starter",
        price_cents=4900,
        features=["Up to 250 locations", "CSV import/export", "Validation workflow", "Email support"],
    ),
    Plan(
        slug="pro",
        name="Pro",
        price_cents=14900,
        features=["Unlimited locations", "Photo uploads", "Priority support"],
    ),
]

FREE_PLAN_SLUG = "free"


def get_plan(slug: str) -> Plan | None:
    return next((p for p in PLANS if p.slug == slug), None)


def list_plans() -> list[Plan]:
    return list(PLANS)
