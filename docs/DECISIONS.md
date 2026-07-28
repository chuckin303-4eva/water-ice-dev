# Architecture Decision Records (ADR)

This file logs significant architectural and process decisions: what was decided, why, what alternatives were considered, and what it costs us later. Add a new entry whenever a decision would be expensive to silently reverse (choice of stack, database, auth model, hosting, branching strategy, major dependency, breaking API/schema change).

Do not log routine implementation choices here — only decisions a future maintainer would otherwise have to reverse-engineer from git history.

## Format

```
## ADR-000X: <short title>
Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded by ADR-000Y

### Context
What problem forced this decision? What constraints applied?

### Decision
What we chose.

### Alternatives considered
What else we looked at, and why it lost.

### Consequences
What this makes easier, what it makes harder, what it locks us into.
```

---

## ADR-0001: Adopt Git branching model and repository governance structure

Date: 2026-07-27
Status: Accepted

### Context
Project is starting from an empty repository. Before any product code is written, we need a consistent workflow so history stays readable, releases stay predictable, and future contributors (including future us) don't have to reconstruct conventions from scratch.

### Decision
Adopt a four-branch model:
- `main` — production only, always deployable
- `develop` — integration branch for completed work
- `feature/*` — new features, branched from and merged back into `develop`
- `bugfix/*` — non-urgent fixes, branched from and merged back into `develop`
- `hotfix/*` — urgent production fixes, branched from `main`, merged into both `main` and `develop`

Establish a `/docs` directory as the single source of truth for architecture, database, API, roadmap, changelog, decisions, security, deployment, user guide, and coding standards — rather than scattering this information across README sections, wiki pages, or tribal knowledge.

Require commit messages to state what changed, why, and what impact it has. Require tests, linting, type checks, and security checks to run before every commit.

### Alternatives considered
- **Trunk-based development (single `main`, short-lived feature branches, feature flags):** simpler, less merge overhead, but assumes CI/CD maturity and feature-flag infra we don't have yet at project start. Revisit once release cadence and team size are known.
- **GitHub Flow (`main` + feature branches, no `develop`):** lower overhead, but gives up a stable integration branch to test against before cutting a release. Revisit if releases become continuous rather than batched.

### Consequences
- Every production release is traceable to a merge into `main`; rollback means reverting a merge commit, not hunting through unrelated commits.
- Adds one extra branch (`develop`) and merge step compared to GitHub Flow — acceptable overhead while the release cadence is not yet continuous deployment.
- This model will be revisited (new ADR, not a silent change) once real usage patterns (release frequency, team size, CI maturity) are known.

---

## ADR-0002: Product direction, stack, and core/module architecture

Date: 2026-07-27
Status: Accepted

### Context
Product scope is now defined: "Ice & Water Intelligence," a commercial SaaS location-intelligence platform for ice and water vending operators (competitors, market opportunity, expansion sites, host businesses, revenue opportunity, resource pooling), designed so the core platform is industry-independent and ice/water vending are the first of potentially several pluggable industry modules.

### Decision
- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL.
- Frontend: React, TypeScript, Vite, Tailwind CSS, Leaflet; charting/table libraries chosen when first needed rather than upfront.
- Auth: JWT + refresh tokens, role-based permissions, Argon2 password hashing.
- Deployment: Docker + Docker Compose, Nginx, GitHub Actions.
- Architecture: core platform (orgs, users, roles/permissions, locations, businesses, scoring interfaces) with industry-specific logic and schema built as separate modules that extend core via FK-linked tables and a defined module interface, never by modifying core tables. See [ARCHITECTURE.md](ARCHITECTURE.md) for the interface sketch and schema.
- Repository stays a single monorepo (backend, frontend, infra, docs together) — pending confirmation (open item 3 below).

### Alternatives considered
- **EAV/JSONB blob for module-specific location data** instead of per-module normalized tables: more "flexible" but fights the explicit "normalized tables, avoid duplicate data" requirement and loses indexability/queryability on module attributes at 100,000+ row scale. Rejected in favor of per-module typed tables.
- **Separate repos per module/service now:** premature at pre-v1 stage with a single maintainer; revisit if/when modules are developed independently by separate teams.

### Resolved items
1. **PostGIS: not adopted for v1.** `locations` uses plain `latitude`/`longitude` numeric columns with standard indexing. Radius/nearest-neighbor queries use bounding-box pre-filtering plus application-level distance calculation. Tradeoff accepted deliberately: simpler stack and hosting (no extension dependency) now, at the cost of query precision/performance at very large scale. Revisit with a new ADR if this becomes a measured bottleneck — never add it back silently.
2. **Multi-tenancy: cross-tenant collaboration, confirmed.** "Resource pooling between operators" is a real cross-tenant feature: organizations can post and respond to resource listings (parts stocking, skilled labor) visible across tenants, not just within one organization's own locations. Implemented as core, industry-agnostic tables (`resource_listings`, `resource_listing_responses` — see [DATABASE.md](DATABASE.md)), since the need for parts/labor isn't ice/water-specific.
3. **Monorepo confirmed** as the ongoing structure, not just a pre-v1 default.

### Consequences
- Adding a new industry (e.g., laundromats, vacuum stations) later means adding a module directory, not touching core schema or core API routes — validates the plugin approach if it holds up through a second module.
- Per-module normalized tables mean N modules eventually means N migration histories to track, but each is independently reviewable and doesn't risk breaking other modules' data.
- Core now includes a genuine cross-tenant data-visibility exception (resource listings) alongside the default tenant-isolated model — the permission layer must distinguish "tenant-private," "cross-tenant-visible-read-only," and "shared market data" rather than a single is-this-my-org check.
- Without PostGIS, "expansion catchment area" (polygon-based) analysis from the original goals is not efficiently supported yet; it's deferred to a future ADR alongside a possible PostGIS adoption once real usage justifies it.

---

## ADR-0003: Full location-intelligence schema — product fields, competitors, and ID strategy

Date: 2026-07-27
Status: Accepted

### Context
Full table list requested: Users, Roles, Permissions, States, Counties, Cities, Locations, Brands, HostBusinesses, Photos, Documents, Reviews, Competitors, Opportunities, ValidationQueue, UpdateLog, Tasks, Settings — plus a detailed required-field list for Locations and a "never overwrite historical information, maintain change history" requirement. Full schema is in [DATABASE.md](DATABASE.md). Three points in that list were in tension with ADR-0002 or otherwise ambiguous and needed an explicit decision rather than a silent default.

### Decision
1. **Product fields on core, not modules.** `serves_ice`, `serves_water`, and `machine_type` live directly on the `locations` table rather than in separate `ice_vending_profiles`/`water_vending_profiles` tables as ADR-0002 originally sketched. Ice and water vending are the entire product today; narrowing the "industry-independent core" principle for these specific fields is an accepted, deliberate trade. A real third industry later would require a migration to extract product-specific fields from core — a deferred cost, not a current problem. This does **not** change the rest of ADR-0002's core/module split (industry-specific *scoring logic* and *UI panels* still belong to modules, not core).
2. **Competitors are site-level records**, not a company roster: `competitors` carries its own `latitude`/`longitude`/`address`, because a location's `competition_score` is computed from nearby competitor density and the map needs competitor pins with real coordinates.
3. **UUID primary keys** on `locations`, `host_businesses`, `competitors`, and `brands` (not just `locations`), so the polymorphic `entity_id` column on `photos`/`documents`/`reviews` is always a single consistent type across everything it can point to.
4. **History via append-only `update_log`**, not full row-versioning: tracked tables are updated in place for current-state reads; every UPDATE also writes one `update_log` row per changed field (old value, new value, who, when, source) in the same transaction. `update_log` rows are never deleted or modified. This satisfies "never overwrite historical information" at the field-change level without versioning every row of every table.
5. New core tables beyond ADR-0002: geography (`states`, `counties`, `cities`), `brands`, `host_businesses`, `competitors`, `opportunities` (workflow layer distinct from `locations.opportunity_score`, which is a computed metric), `photos`/`documents`/`reviews` (polymorphic attachments), `validation_queue`, `update_log`, `tasks`, `settings`.

### Alternatives considered
- **Per-module product-profile tables** (ADR-0002's original plan): more correct for a true multi-industry future, more joins and complexity today for a product that is currently exactly two industries. Rejected for now; revisit if/when a third industry is actually being built, not before.
- **Competitors as a brand-like roster with no coordinates**: simpler table, but would leave competition scoring and map display with no site-level competitor data to work from. Rejected.
- **Mixed ID types** (UUID only on `locations`, serial elsewhere): avoids widening UUID usage, but forces `entity_id` on attachment tables to be stored as text and cast per `entity_type` — more complexity than the UUID columns it avoids. Rejected.
- **Full row-versioning for history**: gives complete point-in-time snapshots per row, not just field diffs, but means every table needs a versioning scheme (append-new-row-on-every-update, or a separate `*_history` table per tracked table). Heavier than the append-only log approach for what's needed right now (auditability of what changed, when, by whom) — revisit if point-in-time full-record snapshots turn out to be needed, not just field-level diffs.

### Consequences
- `locations` is now a wide table (20+ columns) rather than a thin core table with satellite profile tables. Acceptable given decision 1; if a third industry module is added, expect a migration to peel product-specific columns back out.
- Every UPDATE statement against a tracked table (`locations` first, likely others later) must be paired with `update_log` inserts at the application layer — this is a discipline to enforce in code review, not something the schema alone guarantees.
- UUID PKs are marginally larger/slower to index than integers; irrelevant at the stated 100,000+ location scale, and worth it for the ID-type consistency and reduced ID-enumeration exposure across `locations`/`host_businesses`/`competitors`/`brands`.
