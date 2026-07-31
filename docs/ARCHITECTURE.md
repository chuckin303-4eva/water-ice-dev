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
- Leaflet + `leaflet.markercluster` (maps; clustering required at the 100k-location design target, not optional)
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

## Market Refresh Engine (ADR-0004, implemented ADR-0020)

A "Refresh Market" action re-checks existing `locations` against external data sources and proposes changes — it never writes directly to master data.

```
Refresh → Compare → Create Validation Queue entries → Human approval → Update locations → Write update_log
```

This maps directly onto existing tables: `locations` is the master data, `validation_queue` holds proposed changes awaiting a human decision, `update_log` is the permanent change record. `refresh_runs` tracks each invocation (see [DATABASE.md](DATABASE.md)).

**Provider interface** — every external data source is a replaceable module behind one interface, so adding, removing, or swapping a source never touches the comparison/queue/approval logic:

```python
# backend/app/services/market_refresh_providers.py
class MarketDataProvider(Protocol):
    slug: str
    is_free: bool
    def check_location(self, snapshot: LocationSnapshot) -> list[FieldObservation]: ...

class FieldObservation(NamedTuple):
    field_name: str
    observed_value: object
    confidence: float
    source: str        # provider slug, recorded on the validation_queue/update_log row
    observed_at: datetime
```

**v1 providers, as actually shipped (ADR-0020 narrowed this from the original sketch below):**
- **OpenStreetMap** — address drift only, via the same Nominatim reverse-geocoding already used elsewhere in this app. Business-closed, business-moved, new-competitor-POI, and host-tag-changed detection were all dropped for v1 — see "Deferred from the original design" below.
- **US Census** — population and median household income (ACS 5-Year Estimates), plus a derived `growth_rate` (percent change in population between two ACS5 vintages five years apart, not a single Census field). The Geocoder half (coordinates → tract) is keyless; the ACS5 data half requires a free `CENSUS_API_KEY` (signup at https://api.census.gov/data/key_signup.html) — discovered against the real API, not assumed. If the key is unset, `CensusProvider` is skipped for every location (not an error).

**Deferred from the original design, with reasons (ADR-0020):**
- **New-competitor-POI detection (Overpass)** — dropped. ADR-0008 already researched this directly and found OSM has essentially no tagging coverage for ice/water vending machines; building this would be a known near-zero-yield feature, not a hedge against a hypothetical.
- **Business closed/moved, host-tag-changed detection** — dropped. Both need a stable OSM node ID captured at location-creation time to track one specific POI across refreshes, which the schema doesn't have. Deferred pending that groundwork, not built as a guess.
- **Duplicate-location detection** — dropped. "Flag this as a possible duplicate" has no defined resolution/merge workflow on the validation-queue or location model; shipping the flag with no way to act on it would be a half-built feature.
- **USGS / NOAA** — never had an obvious mapping to any of the checks above; still unbuilt, add a concrete adapter only when a specific use is defined.
- **Rating, review-count, and photo-changed detection** — still deferred; no free source carries this data (Google Places/Yelp Fusion are paid), unchanged from the original assessment.

**Paid-API gating (policy, unchanged):** a provider with `is_free = False` stays disabled unless (1) free sources are confirmed unable to supply the data, (2) enabling it is a recorded decision (new ADR) stating why the benefit justifies the cost, (3) its API key comes from an environment variable and is never committed (per [SECURITY.md](SECURITY.md)). Both shipped v1 providers are free — the Census key is a free registration, not a paid API, so this gate hasn't been triggered yet.

**Proposal shape:** one combined `validation_queue` entry per location per run, not one per changed field — every `FieldObservation` from every provider for a given location merges into a single proposal with a combined `reason` string, so a reviewer sees one card per location instead of a flood of near-duplicate cards.

**System-sourced proposals and approval:** a refresh's proposals have `submitted_by = NULL` (no human submitter), which `validation_service.list_queue()` and the approve/reject routes treat as visible to and actionable by every organization's admin — this data is shared platform-wide (ADR-0002), not one tenant's private submission. Approving one uses a new `update_log.change_source = "verification"` (alongside `manual`/`import`/`system`) instead of `"manual"`, so the audit trail honestly reflects how the change was discovered.

**Execution model:** synchronous, triggered by an admin clicking a button — no background job queue or scheduler, matching the original no-new-infrastructure decision. A run processes up to `MAX_LOCATIONS_PER_RUN` (20) locations, oldest/never-checked (`last_verified_at`) first, and can take up to roughly a minute; the frontend button disables itself and labels accordingly rather than pretending it's instant. Every location touched gets `last_verified_at`/`verification_source` updated regardless of whether any drift was found, so "never checked" locations naturally rotate to the front of the next run.

**Endpoints, as actually shipped:**
- `POST /market-refresh/runs` — admin-only, runs synchronously, returns the completed `RefreshRun` summary
- `GET /market-refresh/runs` — admin-only, run history
- `GET /validation-queue` — list pending proposed changes (own org's + all system-sourced)
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
