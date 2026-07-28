# Roadmap

## Now
- Repository governance and project scaffolding (done).
- Resolve open architecture decisions (PostGIS, multi-tenancy scope, monorepo confirmation — see [ARCHITECTURE.md](ARCHITECTURE.md#open-decisions-need-your-sign-off-before-scaffolding)).
- Scaffold backend (FastAPI + SQLAlchemy + Alembic core tables) and frontend (Vite + React + TS + Tailwind shell) per [ARCHITECTURE.md](ARCHITECTURE.md).

## Next
- Core platform: organizations, users, auth (JWT + refresh + Argon2), roles/permissions.
- Core platform: `locations` and `businesses` tables, map shell (Leaflet) with basic pan/zoom/marker rendering.
- First industry module: ice vending — profile table, a first opportunity-scoring pass, module-specific map layer.
- Water vending module, following the same pattern as ice vending.

## Later
- Competitor and market-opportunity scoring refined with real data.
- Expansion-site recommendation (catchment analysis — depends on PostGIS decision).
- Host-business discovery and outreach tooling.
- Resource-pooling features (parts stocking, skilled labor) between operators — scope depends on multi-tenancy decision.
- Additional location-based vending industries as modules beyond ice/water.
- Billing/subscription management for commercial launch.

## Explicitly out of scope (for now)
- Industries beyond ice/water vending, until the module pattern is validated by building two real modules.
- Public API for third-party integrations — internal use only until core stabilizes.
