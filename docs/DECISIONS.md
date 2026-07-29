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

---

## ADR-0004: Market Refresh Engine — provider architecture, paid-API gating, execution model

Date: 2026-07-27
Status: Accepted

### Context
Requested a "Refresh Market" feature that reviews existing locations against external sources, never overwrites data automatically, and routes every proposed change through `validation_queue` → human approval → `locations` update → `update_log`. Required detecting: business closed, business moved, new address, host business changed, rating changed, review count changed, photos changed, duplicate locations, new competitors nearby. Free sources prioritized (OpenStreetMap/Overpass, US Census, USGS, NOAA); paid APIs allowed only when free sources can't provide the data, benefit exceeds cost, and the key is secured. All integrations required to be replaceable modules.

### Decision
1. **Provider interface**: every external source implements `MarketDataProvider` (`slug`, `is_free`, `check_location(location) -> list[FieldObservation]`), so sources are swappable without touching comparison/queue/approval logic. See [ARCHITECTURE.md](ARCHITECTURE.md#market-refresh-engine-adr-0004).
2. **v1 ships free-source detections only**: closed/moved/address/host-business changes and new-competitor detection via OpenStreetMap/Overpass; population/income/growth via US Census; duplicate detection via in-app fuzzy matching (not an external provider). USGS and NOAA are named but not wired into any check — no requested detection maps to what they provide; left as registered-but-unbuilt provider slots rather than force-fit.
3. **Rating/review-count/photo-changed detection is deferred, not built.** No listed free source carries this data — it requires a paid API (Google Places, Yelp Fusion, etc.). Initially approved adding Google Places for this narrow purpose, then reversed after the user clarified they want zero cost incurred at this stage. Deferred to a future ADR made at the point there's budget and a specific provider decision, not built speculatively now.
4. **Paid-API gating is a recorded human decision, not a code check**: a provider with `is_free = False` stays disabled until a new ADR states free sources were confirmed insufficient and the benefit justifies the cost; its key comes from an environment variable per [SECURITY.md](SECURITY.md). "Benefit exceeds cost" can't be verified programmatically — the ADR requirement *is* the gate.
5. **Execution: in-process rate-limited asyncio task, no new infrastructure.** No Redis, no Celery/arq job queue. A run is tracked in a new `refresh_runs` table; a mid-run restart just marks the run incomplete for manual re-trigger. Chosen specifically to avoid an always-on infrastructure cost before a validated need for durable/resumable job execution exists.
6. **New table**: `refresh_runs` (see [DATABASE.md](DATABASE.md)). No changes to `validation_queue`/`update_log` schemas — the refresh engine is a producer of `validation_queue` rows and a consumer of the approval flow, not a new data model.

### Alternatives considered
- **Redis + arq/Celery for job execution**: correct choice once refresh runs are frequent, large, or business-critical enough to need retries/resumability/observability. Rejected for now — adds an always-on paid/operational dependency before there's a user validating the need. Revisit when refresh runs actually need to survive a restart or run on a schedule.
- **Building the Google Places adapter now, disabled by default**: would have the code ready to flip on later. Rejected — maintaining an unused paid-integration adapter is speculative work with no current benefit; building it when there's an actual decision to enable it is cheap enough to defer.
- **Force-fitting USGS/NOAA into existing checks**: rejected — no honest mapping exists between what those APIs provide and what was asked to be detected; better to leave the slot open than invent a use.

### Consequences
- Rating/review/photo drift on existing locations will not be caught until a paid provider is deliberately added later — an accepted gap, not an oversight, given the explicit cost constraint.
- Refresh runs are not resumable and not scheduled in v1 — a run is a manual, one-shot action tied to the lifetime of the process that started it. Acceptable for a manually-triggered button; would need revisiting before this becomes an automated/scheduled job.
- Overpass's public instance is rate-limited; refresh runs must batch and throttle (oldest-`last_verified_at`-first) rather than sweep all locations at once, which means a full refresh of 100,000+ locations happens over multiple runs/sessions, not instantly.

---

## ADR-0005: Autonomous Execution Policy — replaces the pre-work approval gate

Date: 2026-07-28
Status: Accepted (supersedes the approval-gate language in ADR-0001's process rules and the "wait for approval" clause of the architecture-conflict gate added earlier the same day)

### Context
Work on this repo so far required, before any significant change: inspecting the repo, understanding architecture, reviewing docs, identifying dependencies, explaining the proposed approach, and waiting for approval before major architectural changes. In practice this meant frequent stop-and-wait cycles even once project direction was already well established (stack, schema, roadmap all settled by ADR-0002/0003/0004). User replaced this with an explicit autonomous-execution model: keep working through a full milestone, make ordinary implementation and architecture judgment calls independently, and only stop for a short, specific list of situations.

### Decision
Default mode is autonomous: continue working until a logical milestone is complete, do not stop for routine implementation decisions, do not re-ask for approval once project direction is established, and implement the largest coherent unit of work possible before returning control. When multiple valid implementation choices exist, pick the one that best satisfies simplicity, maintainability, security, scalability, performance, and low operating cost, in that rough priority order (consistent with the priorities already stated for this project). Document significant architectural decisions here in DECISIONS.md as they're made, and continue — do not wait for sign-off on the ADR itself.

**Pause only for:**
1. A destructive database migration or irreversible data operation.
2. A change that would knowingly break backward compatibility.
3. Missing credentials, API keys, licenses, or required external resources.
4. A legal, compliance, or platform-policy limitation requiring a user decision.
5. Two or more fundamentally different business strategies that are equally valid, where the choice materially affects the product roadmap.

This supersedes:
- ADR-0001's "explain your proposed approach, wait for approval before major architectural changes" process rule.
- The architecture-conflict gate's "wait for approval" step (added earlier the same day, in response to the `/prompts` request): that gate still applies for *detecting* significant tech debt, duplication, or conflicts with an accepted ADR, but the response changes from stop-and-wait to record-and-proceed — explain the conflict, record the chosen resolution in this file, and continue with the recommended alternative, unless the situation independently matches one of the five pause conditions above (e.g. the "conflict" is actually a destructive migration).
- The PM "give a 6-point status report before implementing, then wait for approval" pre-work checklist: replaced by a post-milestone progress report (completed work, files touched, remaining work, recommended next milestone) given *after* finishing a milestone, followed by immediately continuing to the next one unless interrupted.

Still unaffected: the per-feature business-value/complexity/dependency/risk/impact rundown (PM operating rules, docs/ROADMAP.md) is still stated before starting a feature — it's transparency, not an approval gate, so it no longer pauses for a response.

### Alternatives considered
- **Keep the approval gate for architecture-relevant work, autonomous only for pure implementation details:** closer to the original model; rejected because the user explicitly asked to stop re-asking "when project direction has already been established" — most architecture on this project already is established (ADR-0002/0003/0004), so this middle ground would have kept triggering exactly the friction being removed.
- **Fully unconditional autonomy (no pause list at all):** rejected — irreversible/destructive actions and missing-resource situations genuinely need a human, no matter how established the direction is; the five-item list is narrow specifically so it doesn't reintroduce the old friction while still covering the cases that can't be un-done.

### Consequences
- Multi-step work (e.g. a full Phase 1 feature) can now land as one continuous push with a single post-milestone report, instead of multiple approval checkpoints along the way.
- Architecture and implementation judgment calls made autonomously must still be recorded here when significant — silence is not an option just because approval isn't required anymore.
- Destructive migrations, backward-incompatible changes, missing secrets/licenses, legal/compliance limits, and genuine strategic forks still hard-stop — autonomy has a firm edge, not a soft one.
- If this turns out to move too fast (bad judgment calls slipping through before they're caught), the fix is tightening the pause list or re-adding a checkpoint via a new ADR — not silently reverting to asking before everything again.

---

## ADR-0006: Location prospecting — geocoding, prospect fields, and what stays manual

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 3 (Location management CRUD) had never actually been built — Phase 1 items 1-2 shipped, then work moved to governance/policy and a separate project for several sessions. User asked for it now, framed around a concrete workflow: add a prospective site by pin or address, capture property ownership/management/contacts, expected unit size, power/water/sewer connection details, and pricing estimates, with a "pull this for me where possible" preference, plus call notes and a calendar follow-up button.

### Decision
1. **Geocoding via Nominatim (OpenStreetMap)**, free, no API key — consistent with ADR-0004's "prioritize free sources" default. Used both directions: address → coordinates (creating by address) and coordinates → address (creating by pin), and in both cases also to resolve the state/county/city breakdown into this schema's normalized geography tables via get-or-create, the same pattern already used for other lookup tables in this schema.
2. **17 new prospect fields added directly to `locations`** (property owner/management/contacts, expected unit size, power/water/sewer connection description + company, pricing estimate + notes) rather than a separate table — consistent with ADR-0003's precedent of a wide core `locations` table; these fields aren't industry-module-specific, they apply to prospecting any vending site.
3. **`location_call_notes`**: a new table, not a field, since prospecting naturally produces a *sequence* of calls over time. `follow_up_at` on a note is what a calendar-link endpoint turns into a Google Calendar / Outlook "add event" deep link — no OAuth, no API calls, just a pre-filled URL, which works today with no frontend at all.
4. **`update_log` built now**, not deferred further: ADR-0003 already required an append-only audit trail for exactly this ("never overwrite historical information"), but it had never actually been implemented because Location CRUD didn't exist yet. Building create/update/archive for the first time without wiring this in would have shipped a real, already-agreed requirement's gap, not a new scope decision.
5. **Auto-lookup scope, decided after checking what's actually free (not guessed):**
   - **Power company + commercial rate estimates**: confirmed two free federal data sources exist (EIA electric retail service territories; OpenEI's Utility Rate Database, which supports lookup by lat/lng). Not built this pass — using these properly means either a verified live spatial-query API call or self-hosting a polygon dataset, and the exact API shape wasn't confirmed in the time available. Deferred as a well-defined next step, not abandoned.
   - **Water company**: confirmed a free federal dataset exists (EPA Community Water System Service Area Boundaries, released 2024, ~93-97% population coverage) — newer and less mature than the electric data. Same deferral as power, for the same reason.
   - **Property ownership**: confirmed **no free nationwide source exists** — every option found (Regrid, ATTOM, LightBox) is a paid parcel-data API. Stays manual entry indefinitely, or becomes a future paid-API decision gated the same way LLM/KMS costs are gated on this and the other project — never silently added.
   - **Sewer connection availability**: no equivalent public dataset found at all (unlike power/water). Stays manual indefinitely.

### Alternatives considered
- **A generic "enrichment" table/queue for prospect data** (mirroring LPC's `ai_suggestions`/validation-queue pattern): rejected for now — there's nothing to enrich with yet, since no auto-lookup provider is built. Worth revisiting once the power/water utility lookups are actually implemented, so they go through a review step rather than overwriting fields silently.
- **Storing prospect fields in a separate 1:1 table instead of on `locations` directly**: rejected, consistent with ADR-0003's reasoning — an extra join for every read with no real benefit, since these fields aren't module-specific.

### Consequences
- `locations` grows to 35+ columns. Consistent with the ADR-0003 trade already accepted; still no plan to split it unless a genuine second consumer (a different industry module) needs a different shape.
- Every location create/update/archive now writes to `update_log` — this must stay true for any future write path to `locations`, including whatever the deferred utility-lookup providers eventually do.
- Users will see empty power/water/sewer/pricing fields on new prospects until they fill them in by hand or the deferred lookups are built — this is accurate, not a bug, and shouldn't be quietly "fixed" by fabricating a value.
