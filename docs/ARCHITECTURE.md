# Architecture

## Overview

**Ice & Water Intelligence** is a commercial SaaS location-intelligence platform. It helps ice and water vending operators (and, longer-term, other location-based vending businesses) find and evaluate:

- Competitors
- Market opportunities
- Expansion locations
- Host businesses (sites to place machines at)
- Revenue opportunities
- Technical resources
- Resource pooling (parts stocking, skilled labor) between operators

The platform is multi-tenant: each customer organization has its own users, roles, and data visibility, sharing the same underlying market/location intelligence engine.

## Design principle: core platform + industry modules

The core platform is **industry-independent**. It owns concepts that apply to any location-based vending business: organizations, users, roles/permissions, locations, businesses, market scoring primitives, and the map/reporting UI shell.

Ice vending and water vending (and any future industry) are **modules** that plug into the core. A module is responsible for:
- Its own domain data (module-specific attributes about a location/business), stored in its own normalized tables with a foreign key back to the core `locations`/`businesses` tables — not a shared JSONB blob. This keeps the schema normalized and lets each module evolve its schema independently via its own migrations.
- Its own scoring/opportunity logic (what makes a good ice-vending site is not what makes a good water-vending site).
- Its own reports/UI panels, registered into the core UI shell rather than forking it.

**Narrowed by ADR-0003:** `serves_ice`, `serves_water`, and `machine_type` live directly on the core `locations` table rather than in per-module profile tables, since ice/water vending is the entire product today. Industry-specific *scoring logic* and *UI panels* still belong to modules, not core — only these specific always-present product fields were pulled into core for simplicity. See [DATABASE.md](DATABASE.md) and ADR-0003 in [DECISIONS.md](DECISIONS.md).

Concretely, in the backend this is a Python package interface (sketch, not final code):

```python
# backend/app/core/modules.py
class IndustryModule(Protocol):
    slug: str                     # e.g. "ice_vending"
    def register_models(self) -> None: ...      # SQLAlchemy models, own tables
    def register_routes(self, app: FastAPI) -> None: ...
    def register_scoring(self) -> ScoringStrategy: ...  # opportunity/competitor scoring for this industry
```

Each module lives at `backend/app/modules/<industry_slug>/` with its own models, routes, scoring logic, and Alembic migration files. The core never imports a specific module; modules import and extend the core. This is what makes "industry-independent core, pluggable modules" enforceable rather than aspirational — a new industry is a new module directory, not a change to core tables.

On the frontend, module-specific map layers, filters, and report panels register into a shared shell (map, table, chart primitives) the same way — core doesn't know about "ice" or "water" specifically.

## Tech stack

**Backend**
- Python 3.12, FastAPI
- SQLAlchemy (ORM) + Alembic (migrations)
- Pydantic (request/response schemas, validation)
- PostgreSQL

**Frontend**
- React + TypeScript + Vite
- Tailwind CSS
- Leaflet (maps)
- Charting and table libraries (to be selected when the first data views are built, based on actual data shapes — no chart/table library added speculatively)

**Auth**
- JWT access tokens + refresh tokens
- Role-based permissions (roles/permissions are core-platform concepts; modules can define module-scoped permissions)
- Argon2 password hashing

**Deployment**
- Docker + Docker Compose (local and initial production topology: API container, frontend static build served via Nginx, Postgres container/managed instance)
- Nginx as reverse proxy / static file server / TLS termination
- GitHub Actions for CI (lint, type check, tests, security scan on PR; build on merge to `main`)

## Geospatial queries: plain lat/lng (decided, ADR-0002)

PostGIS was considered and deliberately deferred. For v1, `locations` stores `latitude`/`longitude` as numeric columns with standard indexing; "nearest competitor" / "within N miles" queries run in application code (haversine) or via bounding-box pre-filtering + in-app distance calculation. This is simpler to stand up and host (no extension dependency), at the cost of slower/less precise spatial queries at large scale. Revisit with a new ADR if radius/nearest-neighbor performance becomes a measured bottleneck — do not silently add PostGIS later without recording why.

## Multi-tenancy model (decided, ADR-0002)

Each customer is an `organization`. Users belong to one organization and hold roles scoped to that organization. Location/business/market data is shared (it's market intelligence, not each customer's private data) but saved views, notes, scoring weights, and reports are organization-scoped.

Resource pooling (parts stocking, skilled labor) is explicitly a **cross-tenant, core-platform feature** — not a per-tenant convenience. Organizations can list resource needs/offers and respond to other organizations' listings. This means:
- Core needs an access-control layer distinguishing tenant-private data (own locations, notes, reports) from intentionally cross-tenant-visible data (resource listings, and the shared market/location intelligence itself).
- Resource pooling is industry-agnostic (parts and labor needs aren't ice/water-specific), so it lives in core, not in the ice_vending/water_vending modules.

## Market Refresh Engine (ADR-0004)

A "Refresh Market" action re-checks existing `locations` against external data sources and proposes changes — it never writes directly to master data.

```
Refresh → Compare → Create Validation Queue entries → Human approval → Update locations → Write update_log
```

This maps directly onto existing tables: `locations` is the master data, `validation_queue` holds proposed changes awaiting a human decision, `update_log` is the permanent change record. One new table, `refresh_runs`, tracks each invocation (see [DATABASE.md](DATABASE.md)).

**Provider interface** — every external data source is a replaceable module behind one interface, so adding, removing, or swapping a source never touches the comparison/queue/approval logic:

```python
# backend/app/core/market_refresh/providers.py
class MarketDataProvider(Protocol):
    slug: str
    is_free: bool
    def check_location(self, location: LocationSnapshot) -> list[FieldObservation]: ...

class FieldObservation(NamedTuple):
    field_name: str
    observed_value: Any
    confidence: float
    source: str        # provider slug, recorded on the validation_queue/update_log row
    observed_at: datetime
```

**v1 providers (all free, all enabled by default):**
- **OpenStreetMap / Overpass API** — business closed (POI removed/tagged disused), business moved (coordinates shifted beyond a threshold), address changed, host business tag changed, new competitor POIs (same amenity/shop tag) within radius of a location.
- **US Census API** — population, median income, growth rate for a location's tract/block group.
- **USGS / NOAA** — registered as available provider slots but not wired into any check yet; neither has an obvious mapping to the detections requested (closed/moved/rating/reviews/photos/duplicates). Left unbuilt rather than force-fit into a check that doesn't need them — add a concrete adapter only when a specific use (e.g., flood-zone or elevation as a scoring factor) is defined.
- **Duplicate detection** is a separate comparison pass, not a provider: locations within a bounding box of each other are fuzzy-matched on name + address; matches above a threshold create a `validation_queue` entry (`entity_type = "location_duplicate"`).

**Rating, review-count, and photo-changed detection is deferred, not built.** No free source in this list carries ratings/reviews/photos — that data lives behind paid APIs (Google Places, Yelp Fusion). Per your paid-API policy and current no-cost constraint, this ships later as its own decision (a new provider module plus an explicit config flag, API key via environment variable, and a recorded justification in DECISIONS.md) — not as part of v1.

**Paid-API gating (policy, operationalized):** a provider with `is_free = False` is disabled unless (1) free sources are confirmed unable to supply the data, (2) enabling it is a recorded decision (new ADR) stating why the benefit justifies the cost, (3) its API key comes from an environment variable and is never committed (per [SECURITY.md](SECURITY.md)). "Benefit exceeds cost" is a business judgment the code cannot verify — the gate is the recorded human decision, not an automated check.

**Confidence score:** starts from a fixed per-source reliability weight (government/official sources score higher than community-maintained ones), adjusted up when a second provider independently reports the same value and down on disagreement. Kept deliberately simple for v1 — refine once real refresh data shows where it's wrong, not before.

**Execution model:** an in-process, rate-limited asyncio task (no new infrastructure — no Redis, no job queue), started by `POST /market-refresh/run` and tracked in `refresh_runs` for progress polling. If the process restarts mid-run, that run is marked incomplete and simply re-triggered — an acceptable trade for a manually-triggered, non-critical-path job at this stage, chosen specifically to avoid adding an always-on infrastructure cost before there's a validated need for one. Runs process locations in batches (oldest `last_verified_at` first) rather than all 100,000+ at once, both to respect free-API rate limits (Overpass's public instance in particular is aggressively throttled) and to keep individual runs finishing in a reasonable time.

**Endpoints (sketch):**
- `POST /market-refresh/run` — start a run
- `GET /market-refresh/runs/{id}` — status/progress
- `GET /validation-queue` — list pending proposed changes
- `POST /validation-queue/{id}/approve` — applies `proposed_changes` to the target entity, writes `update_log` rows, marks the queue entry approved
- `POST /validation-queue/{id}/reject` — marks rejected, no changes applied

## Repository layout (proposed)

```
water-ice-dev/
  backend/
    app/
      core/            # org, user, role/permission, location, business, auth, scoring interfaces
      modules/
        ice_vending/
        water_vending/
      api/             # FastAPI routers, versioned
      db/              # SQLAlchemy session/engine setup
    migrations/        # Alembic
    tests/
    pyproject.toml
  frontend/
    src/
      core/            # map shell, table/chart primitives, auth, layout
      modules/
        ice_vending/
        water_vending/
    package.json
  infra/
    docker-compose.yml
    nginx/
  .github/
    workflows/
  docs/                # this directory
```

## Non-functional requirements

- Designed for 100,000+ locations: normalized schema, indexed foreign keys, pagination on all list endpoints, no N+1 query patterns in list/map views.
- Multi-tenant data isolation enforced at the query layer (every tenant-scoped query filtered by organization_id), not just at the UI layer — with an explicit exception path for the cross-tenant resource-pooling feature.

## Decisions log

Stack, core/module architecture, geospatial approach, multi-tenancy/resource-pooling scope, and monorepo structure are all decided — see [DECISIONS.md](DECISIONS.md) ADR-0001 and ADR-0002 for the recorded rationale.
