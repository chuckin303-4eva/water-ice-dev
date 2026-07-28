# Roadmap

## Now
- Repository governance and project scaffolding (done).
- Architecture decisions resolved: plain lat/lng (no PostGIS for v1), cross-tenant resource pooling, monorepo confirmed — see [DECISIONS.md](DECISIONS.md) ADR-0002.
- Scaffold backend (FastAPI + SQLAlchemy + Alembic core tables) and frontend (Vite + React + TS + Tailwind shell) per [ARCHITECTURE.md](ARCHITECTURE.md).

## Next
- Core platform: organizations, users, auth (JWT + refresh + Argon2), roles/permissions.
- Core platform: `locations` and `businesses` tables, map shell (Leaflet) with basic pan/zoom/marker rendering.
- First industry module: ice vending — profile table, a first opportunity-scoring pass, module-specific map layer.
- Water vending module, following the same pattern as ice vending.
- Market Refresh Engine v1 (ADR-0004): "Refresh Market" button, OpenStreetMap/Overpass + US Census providers, duplicate detection, validation queue + approval UI, update_log write-through.

## Later
- Competitor and market-opportunity scoring refined with real data.
- Expansion-site recommendation (polygon-based catchment analysis — deferred until/unless PostGIS is adopted; v1 uses radius-based approximation instead).
- Host-business discovery and outreach tooling.
- Cross-tenant resource-pooling marketplace (parts stocking, skilled labor) — core tables defined in [DATABASE.md](DATABASE.md), UI/matching logic built after core platform and first industry module are live.
- Rating/review-count/photo-changed detection via a paid provider (e.g. Google Places) — deferred by ADR-0004 until there's budget and a deliberate decision to enable one; not built speculatively.
- Durable/scheduled market refresh (background job queue) — deferred by ADR-0004 until refresh runs need to survive restarts or run on a schedule, not built ahead of that need.
- Additional location-based vending industries as modules beyond ice/water.
- Billing/subscription management for commercial launch.

## Explicitly out of scope (for now)
- Industries beyond ice/water vending, until the module pattern is validated by building two real modules.
- Public API for third-party integrations — internal use only until core stabilizes.
