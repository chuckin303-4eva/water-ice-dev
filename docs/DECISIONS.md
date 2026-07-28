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
