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

---

## ADR-0007: Interactive map frontend — stack, tile provider, and CORS

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 4. This project had no frontend at all before this. User asked for the map with two open questions: which tile provider, and how minimal the add-prospect form should be. Answers given: pick a free tile provider now and swap before real users; keep the add-prospect form to pin/address only, everything else filled in later via the detail panel (which ADR-0006 already built the fields and endpoints for).

### Decision
1. **Stack: React 19 + TypeScript + Vite + Tailwind v4 + Leaflet (`react-leaflet`)**, no separate state-management library — the map's state (locations list, selected location) is small enough for plain `useState`/`useEffect`, and a second dependency isn't justified yet.
2. **Marker clustering via `leaflet.markercluster`**, wired in imperatively through `useMap()` — required, not optional polish, given the schema's own 100,000+ location design target; an unclustered map would be unusable at that scale.
3. **Tile provider: raw OpenStreetMap tiles for now, swap before production.** Confirmed via research (not assumed) that `tile.openstreetmap.org` explicitly prohibits commercial/production use in its own usage policy and can withdraw access without notice. Free-tier alternatives with no credit card required (MapTiler, Stadia Maps) exist for when this becomes a real product in front of users; paid tiers (~$25/mo) are a future cost tied to real commercial traffic, not a cost today. Tile URL/attribution are env vars (`VITE_TILE_URL_TEMPLATE`, `VITE_TILE_ATTRIBUTION`) specifically so this swap is a config change, not a code change.
4. **Add-prospect form: pin or address only.** Everything else (property owner, contacts, utilities, pricing) is filled in afterward through the existing detail panel / update endpoint (ADR-0006) — no duplicate "create" and "edit" field sets to keep in sync.
5. **Backend CORS added** (`CORSMiddleware`, origin list from a new `cors_origins` setting, defaulting to the Vite dev origin `http://localhost:5173`): the backend had no frontend to talk to before this, so it had never been configured. Origin list is env-driven so non-dev origins can be added later without a code change.
6. **`localStorage` for the access token**, not an httpOnly cookie — simplest option for a not-yet-public-facing internal tool; flagged in code as an XSS trade-off to revisit before public exposure, not treated as a solved problem.

### Alternatives considered
- **A paid tile provider from day one**: rejected — no real users yet, so there's no traffic to justify a recurring cost; the free-tier swap is a config change away when it's actually needed.
- **httpOnly cookie for auth token**: rejected for now — requires backend session/cookie infrastructure that doesn't exist yet and isn't justified before the product is customer-facing; recorded as a known gap, not ignored.

### Consequences
- The map will need a tile-provider swap (env var change) before any real/external user sees it — tracked here and in ROADMAP.md so it isn't forgotten.
- `cors_origins` must be updated (via env, not code) whenever a new frontend origin needs to reach this API (a deployed frontend URL, a staging environment, etc.).
- No automated frontend tests exist yet — verification for this feature was `tsc -b` (type-check), a full `vite build`, and manual end-to-end verification in a real browser against the real backend (login, map load, add-prospect by address, call note, calendar link) plus direct API verification via curl. Establishing a frontend test pattern (Vitest + React Testing Library, most likely) is unscheduled work, not an oversight.

---

## ADR-0008: Competitor tracking — schema, map color-coding, and why Denver isn't pre-populated

Date: 2026-07-29
Status: Accepted

### Context
User asked to focus the map on the Denver metro area, populate it with existing competitor locations, color-code pins by type (yellow = new prospect, green = good-scoring prospect / active, orange = competitor), and be able to click a competitor to see address, inside/outside, brand, size, ice-vs-water, and price. Competitors were designed in ADR-0003 (`competitors` table) but never actually built — Phase 1's roadmap also never explicitly scheduled them as their own line item, even though the schema anticipated them from day one.

### Decision
1. **Competitors implemented now, pulled forward into Phase 1** (not originally a numbered roadmap item) — flagged here per the PM operating rules rather than built silently, because it's directly requested and arguably as central to "location intelligence" as the map itself. ROADMAP.md updated accordingly.
2. **Schema widened beyond ADR-0003's original design**: added `is_inside`, `machine_size`, `ice_price`, `water_price`, `price_notes` to `competitors` — needed for the click-to-view panel the user asked for; the original design only had `estimated_market_share`/`last_observed_date`/`source`/`notes` beyond the basics.
3. **No `update_log` for competitors** (unlike `locations`): that guarantee is specifically about not overwriting an operator's own prospecting history; a competitor row is an observation of a rival, expected to be corrected/replaced freely, not an audited record. `DELETE` is a real hard delete here, not the soft-archive `locations` uses.
4. **Map color logic**: `archived` -> slate, `active` -> green, `prospect` -> green once `opportunity_score` is populated and above a threshold, else yellow. Competitors get their own marker layer: orange, and a **square** icon (not just a different color) -- color alone isn't a reliable cue for the ~8% of users with red-green color vision deficiency, and orange/yellow/green are exactly the colors that can be confused. The `opportunity_score` threshold (70) is a placeholder with no real basis yet -- Basic Scoring (Phase 1 item 5) hasn't been built, so every current prospect is yellow regardless of the exact number; this is forward-compatible and will start mattering once that feature ships.
5. **Denver metro is NOT pre-populated with competitor data, and no fabricated rows were created.** Researched (not assumed) whether a free, automated source exists: Twice the Ice, Kooler Ice, and Ice House America all gate their machine locators behind mobile apps or an interactive zip-code map -- no static, scrapeable address list exists on any of their sites (confirmed via direct fetch of their locator pages). Primo/Glacier Water's dispenser finder is the same pattern. A direct Overpass (OpenStreetMap) API query for the Denver bounding box was also attempted; the public instance was overloaded at the time, but even when available, ice/water vending kiosks are essentially never tagged in OSM (that tag set is used for snack/drink machines, not this niche) -- this is a real data-coverage gap, not a query bug. Inventing plausible-looking competitor names/addresses to "fill in" the map was rejected outright -- this is a real commercial tool and fake site data could actively mislead a placement decision, the same honesty bar already applied to utility/property lookups in ADR-0006.

### Alternatives considered
- **A paid Places API (e.g. Google Places) to auto-populate competitors**: would work, but is a new recurring cost -- gated the same way KMS/LLM-API costs are gated on this and the related project, requires explicit sign-off, not a default.
- **Waiting for the Market Refresh Engine (ADR-0004) to eventually cover this**: rejected as the *only* path -- that's Phase 3, and the user asked for this now; manual entry is a legitimate interim path, not a workaround.
- **Letting the user enter competitors only through a future admin/import flow**: rejected -- the same pin/address map-click pattern already built for prospects (ADR-0007) works just as well here and ships today.

### Consequences
- The practical path to real Denver data is the operator's own market knowledge, entered through the same "+ Add Competitor" map control used to verify this feature -- an operator in this specific niche market almost certainly knows their local rivals better than any generic API would.
- A paid Places API remains available as a future opt-in if manual entry proves too slow at scale -- requires explicit sign-off before building, per the established cost-averse default.
- `competitors` has no organization scoping, same as `locations` (ADR-0002) -- shared platform-wide intelligence, not per-tenant.

### Addendum (same day): rejected a Maps-scraping browser extension, built copy/paste-assisted entry instead
User's follow-up ask was a browser extension to scrape Google/Bing Maps search results (including photos) to speed up manual competitor entry. Declined to build this: both platforms' terms of service prohibit automated extraction of listing data, Google has pursued legal action against scraping operations at commercial scale, listing photos aren't freely licensed for reuse in another commercial product, and DOM-scraping code breaks on an unpredictable timeline as these sites change. This isn't a capability gap to route around -- it's a real legal-exposure decision that has to be the user's, made with the trade-offs stated plainly, not built quietly.

Instead built a copy/paste-assisted quick-entry: the user manually selects and copies visible text from a listing in their own browser (ordinary browser functionality, not automation, no different from them retyping it), pastes it into a textarea in the Add Competitor control, and `parseMapsListing()` (frontend-only, `src/core/map/parseMapsListing.ts`) heuristically splits out a name (first line) and address (the line containing a ZIP code, or failing that, one starting with a street number) to prefill the form fields for review before saving. No network request to Google/Bing is made by our code at any point -- the only "extraction" happening is client-side string parsing of text the user already has on their clipboard. Photo upload remains unbuilt (Phase 2 "Photos," ROADMAP.md) and wasn't addressed by this change; when it exists, saving/uploading an image the user found is the same manual, non-automated pattern, not scraping.

**Bug found and fixed while building this**: `AddProspectControl` and `AddCompetitorControl` are rendered as children of react-leaflet's `<MapContainer>`, which places them as real DOM descendants of Leaflet's own map container div. Leaflet's `useMapEvents` click handler listens on that container, so clicking *any* button or input inside these overlay panels (not just the map itself) bubbled up and also fired the "user clicked the map to place a pin" handler -- silently creating an extra prospect/competitor at whatever screen coordinate the button occupied, in addition to the one actually being submitted. Leaflet's own built-in controls (zoom in/out) avoid exactly this via `L.DomEvent.disableClickPropagation`; added a small `useStopMapClickPropagation` hook (`src/core/map/useStopMapClickPropagation.ts`) applying the same fix to both Add controls and both detail panels. Verified via real browser testing (network log showed exactly one `POST` per submission, before and after the fix showed the difference) -- no evidence this created bad data in earlier verification passes (their event logs showed single POSTs too), but it was a live landmine for the first real user click.

### Addendum (same day): compact manual-entry form replaces paste-matching; added brand/contact/follow-up fields
User tried the paste-matching UI once and preferred a straightforward manual form instead -- plain small fields (location name, brand, address, website, phone, contact name, email), no text-matching step, plus the same follow-up-to-calendar pattern already built for location call notes. `parseMapsListing.ts` was removed (dead code, no longer called from anywhere) rather than left unused.

Schema widened again: `brand` (free text with a `<datalist>` of suggestions -- Twice the Ice, Kooler Ice, Watermill Express -- rather than a link to the shared `brands` table, since this needs no more structure than an autocomplete hint and competitors aren't tenant-owned records the way a location's brand relationship might eventually be), `website`, `phone`, `contact_name`, `contact_email`, and `follow_up_at`. `follow_up_at` lives directly on `competitors` (not a separate call-notes table like locations' `location_call_notes`) since competitors don't need a call history -- one pending follow-up at a time is enough, consistent with ADR-0008's "corrected freely, not audited" treatment of this table. `GET /competitors/{id}/calendar-link` reuses `calendar_link_service` unchanged (it was already generic over title/start/details/location).

---

## ADR-0009: Basic scoring — what's computed for real vs. deferred

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 6. `locations` has had five score-shaped columns (`visibility_rating`, `traffic_score`, `population`, `median_income`, `growth_rate`, `competition_score`, `opportunity_score`, `confidence_score`) since the original Phase 1 schema (ADR-0003) — none had ever been populated, exposed via the API, or given a defined scale. The map (ADR-0007/ADR-0008) already reads `opportunity_score` to color prospect pins green; this feature is what starts writing real values to it.

### Decision
1. **`competition_score`: real and automatic.** Computed from actual distance to nearby rows in `competitors` (now populated per ADR-0008) — app-level haversine, no PostGIS, per ADR-0002. Bounding-box pre-filter, then exact distance on the smaller candidate set. Each competitor within 10 miles contributes `100/(1+distance_miles)`, summed and capped at 100. Zero nearby competitors correctly yields 0 — a real, confident answer, not a missing value.
2. **`opportunity_score`: real, but requires input.** A weighted composite: 35% visibility, 35% traffic, 30% `(100 - competition_score)`. `visibility_rating` and `traffic_score` are newly exposed via the API for the first time as manually-entered 1-10 ratings (their scale was never defined before this). **`opportunity_score` is `None` until both are set** — computing a confident-looking number from missing inputs would misrepresent the score, the same honesty bar as every other "no free data source" decision in this project (ADR-0006, ADR-0008).
3. **`population`/`median_income`/`growth_rate` are NOT used.** No free demographic data source has been wired — that's the Market Refresh Engine (ADR-0004), scheduled Phase 3. Leaving them out of the formula entirely rather than defaulting them to zero, which would silently bias every score toward "bad opportunity."
4. **`confidence_score` measures input completeness, not site quality**: 0 with neither rating set, 50 with one, 100 with both.
5. **Recalculation**: automatic on every location create/update (covers the common case — rating a site, or moving its pin). A standalone `POST /locations/{id}/recalculate-score` covers the case a create/update doesn't: new competitor data appeared nearby without the location itself changing. No reactive recompute-on-every-nearby-competitor-write for this "Basic" pass — that's real complexity (which locations are "nearby" a given competitor write) deferred until it's actually needed, not an oversight.

### Alternatives considered
- **Defaulting missing demographic/rating fields to a neutral midpoint (e.g., 50) to always produce a number**: rejected — indistinguishable from a real "average" site, which is worse than an honest `None` that visibly prompts the user to rate the site.
- **A reactive trigger that recomputes every location's score whenever any competitor changes**: rejected for v1 — real cost (which locations are within range of a given competitor write) with no demonstrated need yet at this data volume; the explicit recalculate endpoint covers the same need on demand.

### Consequences
- Every prospect stays yellow on the map until its visibility and traffic are rated by hand — this is accurate, not a bug: no real opportunity signal exists yet for an unrated site.
- If `competitors` data changes near a location that was already scored, its `competition_score`/`opportunity_score` go stale until either the location itself is edited or `recalculate-score` is called — a known, documented limitation, not silent staleness.
- `visibility_rating`/`traffic_score` scale (1-10) is now fixed by this ADR; changing it later is a breaking change to every already-scored location.

---

## ADR-0010: Filters — server-side, opt-in capability narrowing

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 7. The map fetches full `locations`/`competitors` lists with no pagination; ROADMAP.md's own reasoning for this feature ("map becomes unusable at real data volume") points at eventual scale, not just today's small dev dataset.

### Decision
1. **Server-side, not client-side.** `GET /locations` and `GET /competitors` gained query-param filters (`statuses`, `serves_ice`, `serves_water`, `min_opportunity_score`, `brand`) applied in the SQL query, not filtered out of an already-fetched in-memory array. Consistent with the stated 100k-location design target (ARCHITECTURE.md non-functional requirements) — filtering in the database is what actually helps at scale; filtering client-side after fetching everything wouldn't.
2. **`statuses` replaces the narrower single-value `status_filter`** with a repeatable multi-value query param (`?statuses=prospect&statuses=active`), so the UI can support "show these two, hide that one" with checkboxes rather than a single dropdown. No external consumers exist yet (`GET /locations` is not a published third-party API — see ROADMAP's "explicitly out of scope"), so this is a clean rename, not a breaking change to anyone outside this repo.
3. **`serves_ice`/`serves_water` are opt-in narrowing, not exclusion.** Both default to "don't care" (omitted = no filter); checking one or both means "must serve at least one of the checked capabilities" (OR, not AND). A strict "must match exactly what's checked" filter would hide every freshly-created prospect/competitor, since `serves_ice`/`serves_water` both default to `false` until someone fills them in — the same "don't let an empty field silently look wrong" principle behind every other honesty decision in this project (ADR-0006, ADR-0008, ADR-0009), applied to filter UX rather than data population.
4. **`min_opportunity_score` naturally excludes unrated locations** (`opportunity_score IS NULL` never satisfies `>=`), which is correct: an unrated site has no opportunity signal to compare, not a low one.
5. **"Show competitors" is a pure client-side visibility toggle**, not a query param — it doesn't change what's fetched, just whether the already-fetched competitor layer renders. No backend involvement needed for a pure show/hide.

### Alternatives considered
- **Client-side filtering of the already-fetched full lists**: simpler to build, but works against the schema's own stated scale target and would need to be redone once pagination exists anyway. Rejected in favor of doing it right once.
- **Keeping `status_filter` as single-value and adding a second param for a second status**: rejected as needless API surface growth compared to one repeatable `statuses` param.

### Consequences
- Every filter change triggers a new network request (no debounce added yet) — acceptable at current data volume; revisit if it becomes a real UX issue once pagination/larger datasets exist.
- `min_opportunity_score` only has real meaning once Basic Scoring (ADR-0009) actually produces scores for rated sites — consistent with that feature's own stated limitation, not a new one.

---

## ADR-0011: Import CSV — minimal columns, server-side row cap, rate-limit-aware

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 8. ROADMAP.md's own stated value: "Lets a prospective customer load their existing location list immediately instead of manual entry." Each row still needs geocoding (address → coordinates, or coordinates → address/geography breakdown) through the same Nominatim service every other location create already uses — which has a documented ~1 request/second usage policy that a normal one-at-a-time human workflow never stressed, but a bulk import obviously does.

### Decision
1. **Minimal v1 column set**: `address` (or `latitude`+`longitude`), `serves_ice`, `serves_water`, `notes`. Same "minimal add, fill in the rest later via the detail panel" split as every other prospect-creation path (ADR-0007) — no attempt to support the full 30+ field prospecting schema through a CSV in this pass.
2. **Rows are geocoded sequentially with a fixed ~1.1s delay between them**, reusing `location_service.create_location` per row (not a separate bulk code path) so every existing single-create behavior — geography resolution, score calculation — applies identically to imported rows. This means a large import is slow by design, not a bug: it's the cost of respecting Nominatim's real usage policy rather than hammering it.
3. **A 100-row cap per import file**, enforced before any row is processed, so a request's duration is bounded (worst case ~2 minutes) rather than open-ended. Rejected outright (422) if exceeded, not silently truncated.
4. **Partial success, not all-or-nothing**: a bad row (missing address and coordinates, unparseable data, a geocoding failure) is recorded as a per-row error and the import continues; the response reports `{total_rows, created, errors}` so the user can fix and re-import just the failed rows.
5. **Row-level errors don't roll back already-created rows** — each row's `create_location` call commits independently (matching that function's existing behavior), so a failure on row 50 of 100 doesn't undo rows 1-49.

### Alternatives considered
- **A background job / async processing with a status-polling endpoint**: more correct at real scale, but real infrastructure (job queue) this project has deliberately deferred elsewhere (ADR-0004's Market Refresh Engine is Phase 3, in-process only). A synchronous request bounded by the row cap is adequate for a "doesn't have to be perfect to demo" MVP and needs no new infrastructure.
- **Supporting the full prospecting field set via CSV columns**: rejected for v1 as unnecessary scope — matches the same reasoning ADR-0007 used to keep the map's manual add-prospect flow to pin/address only.
- **Silently truncating a too-large file to the row cap**: rejected — silently dropping rows the user didn't know would be dropped is worse than a clear upfront rejection telling them the limit.

### Consequences
- Importing 100 rows takes on the order of ~2 minutes (rate-limit delay dominates) — a real, disclosed trade-off, not a performance bug to "fix" later without also revisiting the free-Nominatim-usage decision (ADR-0004/ADR-0006) that caused it.
- New runtime dependency: `python-multipart` (required by FastAPI's `UploadFile`/`File` for parsing multipart/form-data uploads).

---

## ADR-0012: Admin dashboard — self-serve registration, two-role model, no permission-slug system

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 9. `organizations`/`users`/`roles`/`permissions`/`role_permissions`/`user_roles` have existed as schema since the original Phase 1 migration (ADR-0003-era), but nothing had ever populated or enforced them: no role/permission concept existed anywhere in the code, no role rows existed in any database, and the only way to create a user at all was `backend/scripts/seed_dev_user.py` — whose own docstring, and `docs/API.md`, both explicitly said self-serve registration was deferred to this exact feature.

### Decision
1. **Self-serve registration** (`POST /auth/register`): creates a brand-new `Organization` plus its first `User`, who becomes that org's admin, and logs them in immediately (returns tokens, same shape as login). No email verification, no CAPTCHA — both real hardening gaps for a public signup endpoint, explicitly deferred and named here rather than silently shipped as "handled."
2. **Two system-wide roles only: "admin" and "member".** No arbitrary role names, no fine-grained permission-slug system built or enforced — `permissions`/`role_permissions` stay schema-only and unused. Building a granular permission UI with zero real per-capability checks to gate would be pure unused scaffolding (YAGNI); role-based admin/member is what's actually needed to gate the two new capabilities this feature adds (create a teammate, change someone's role/active status). Nothing else in the app becomes role-gated — locations/competitors stay shared platform-wide data per ADR-0002, unaffected by this.
3. **Roles are get-or-created lazily** (`organization_service.get_or_create_role`), the same pattern geography rows already use, rather than seeded via a one-time data migration — avoids migration/dev-db seed drift. `Role.organization_id` stays `NULL` for both roles, per that column's own documented "nullable for system-wide roles" intent.
4. **No email invite flow.** An admin creating a teammate sets a real password directly, shown once in the response/UI, which the admin shares out-of-band — there's no email service in this project to send an invite through (same honesty pattern as every "no automated X" decision elsewhere: ADR-0006, ADR-0008). Building a fake-looking "invite sent" flow that doesn't actually send anything would be worse than being upfront about it.
5. **Org lockout prevention: self-modification is blocked, and that's the whole guard.** The only mutation path for `is_active`/role is `PUT /organizations/users/{id}` (admin-only), which unconditionally rejects `user_id == caller's own id` (400). Combined with every org starting with exactly one admin at registration, this alone makes 0 active admins in an org structurally unreachable — whoever calls this endpoint on someone else is necessarily a different, currently-active admin, so at least one admin always survives. An earlier draft of this feature also added a "count active admins, block if <=1" check; it was **provably dead for its intended purpose** given the self-modification block, and it produced a real false-positive (blocking a harmless role change on an already-inactive admin) instead of ever preventing a real lockout — removed rather than patched. See `organization_service.py`'s module docstring for the full reasoning.
6. **First real use of client-side routing.** `react-router-dom` was installed as a dependency when the map frontend was built (ADR-0007) but never actually wired in — `App.tsx` just showed the map or the login screen based on a boolean. This feature needed real pages (`/login`, `/register`, `/`, `/admin`) with an actual admin-only route guard, so it's the first thing to use the dependency that was already there.

### Alternatives considered
- **Fine-grained permission slugs from the start** (using the existing `permissions`/`role_permissions` schema as designed): rejected — no endpoint anywhere needs to distinguish "can edit locations" from "can manage billing" yet; building the management UI for permissions nothing checks would be pure theater. Revisit with a new ADR if/when real per-capability gating is actually needed.
- **Keeping registration deferred further, building only org-internal user management**: rejected — the stale docs (seed script, API.md) explicitly promised registration would arrive with this feature; leaving it deferred again would repeat the same promise-without-delivery gap.
- **A "last admin" count-based lockout guard**: rejected after being built and found dead — see point 5.

### Consequences
- No schema changes were needed — every table this feature uses (`organizations`, `users`, `roles`, `user_roles`) already existed. Purely additive service/route/frontend work.
- `docs/API.md` and the seed script's docstring both referenced this feature as "Phase 1 item 8" (stale relative to the current roadmap, where it's item 9, since Import CSV was inserted ahead of it) — corrected as part of this change.
- A future real permission system, if ever needed, has to be designed fresh rather than grown from `role_permissions` as originally sketched, since that path was deliberately left unused rather than partially built.

---

## ADR-0013: Export CSV — full field set, filter-aware, built for both entities

Date: 2026-07-29
Status: Accepted

### Context
Phase 1 item 10, the last item on the current Phase 1 roadmap. ROADMAP.md's own framing: "Portability/trust feature. Valuable, not blocking initial usability." Import CSV (ADR-0011) established the CSV-handling pattern for locations; export is materially simpler since there's no geocoding and no Nominatim rate limit to respect — it's a synchronous read of whatever's already in the database.

### Decision
1. **Full field set, not the minimal import columns.** Import intentionally stays minimal (ADR-0011's "fill in the rest later" reasoning), but export is a portability/backup operation, not a data-entry form — more data is strictly better here. Reuses each entity's existing `assemble_response` (via `LocationResponse`/`CompetitorResponse`'s own field list) so the exported columns can never drift from what the API itself considers a location/competitor's full shape.
2. **Filter-aware**: `GET /locations/export` and `GET /competitors/export` accept the exact same query params as their `GET /locations`/`GET /competitors` list endpoints (ADR-0010) and export only the matching rows. "Export what I'm currently looking at" just works without a separate export-specific filter UI.
3. **Built for both locations and competitors**, not just locations. Import CSV was locations-only (competitors didn't exist yet when it shipped); now that the pattern and both entities exist, adding the second export endpoint was small incremental cost for a more complete portability story — seeing competitors on the map but being unable to export them would have been an odd gap.
4. **Synchronous, no row cap.** Unlike import, there's no per-row external network call (no geocoding), so there's no rate-limit-driven reason to cap size or delay — a straight `SELECT` + CSV serialization scales fine at the row counts this product handles today.
5. **Route registration order matters again**: both `GET /{id}/export` routes are declared *before* their respective `GET /{id}` routes in the same file, for the same reason as `POST /import` needed no such care (different HTTP method) but export does (same GET method) — Starlette matches routes in registration order, and `/export` would otherwise be swallowed by `/{location_id}`'s path shape and fail UUID parsing before ever reaching the export handler.

### Alternatives considered
- **A single combined export (locations + competitors in one file/zip)**: rejected — two flat CSVs with different, unrelated column sets is simpler to consume in a spreadsheet than one file mixing shapes or a zip archive nobody asked for.
- **Exporting only the minimal columns import accepts, for column-set symmetry**: rejected — import and export serve different purposes (data entry vs. portability/backup) and don't need matching scope just for its own sake.

### Consequences
- The exported CSV's column set is coupled to `LocationResponse`/`CompetitorResponse` — adding a field to either response automatically appears in the export next time, with no separate export-schema to keep in sync.
- No streaming for very large exports (the whole CSV is built in memory as one string) — acceptable at current scale; revisit if/when real row counts make that a measured problem, consistent with this project's "don't build for a scale that doesn't exist yet" pattern elsewhere.

---

## ADR-0014: Validation workflow — opt-in per-organization review queue

Date: 2026-07-29
Status: Accepted

### Context
Phase 2, first item. `validation_queue` was designed in ADR-0003 as part of the original full schema but never implemented — every location write (create/update/import) has always applied directly, regardless of who made it. The product need: an org owner running a team of non-admin data-entry staff may want a chance to review new/changed locations before they go live, rather than trusting every submission unconditionally.

The obvious naive design — "non-admins always get queued" — was checked against actual test/runtime behavior before writing any code: every existing user fixture and every real dev/seed user has no row in `user_roles` at all, and `get_user_role_name`'s documented fallback for that case is `"member"`. An unconditional queue-if-non-admin rule would have silently changed real existing behavior for every current user of the app the moment this feature shipped — a backward-compatibility break, one of the five explicit pause conditions in ADR-0005.

### Decision
1. **Opt-in per organization, default off.** New `organizations.require_review_for_submissions` boolean, `default=False`. No existing organization's behavior changes unless an admin explicitly turns it on via `PUT /organizations/settings` (admin-only; `GET /organizations/settings` is any authenticated user, so a non-admin can at least see whether it's on). This sidesteps the backward-compat pause condition by construction rather than by asking for an exception to it.
2. **Even when on, admin writes always apply directly.** The queue exists to let an admin review *other people's* submissions, not their own — an admin gaining an approval step for their own work would be pure friction with no safety benefit, since they already have full write access.
3. **Scope is narrow: only `POST /locations`, `PUT /locations/{id}`, and per-row `POST /locations/import`.** Does not apply to archiving (`DELETE /locations/{id}`), score recalculation, competitors, or call notes — this feature is specifically about "is this location data trustworthy," not a general-purpose approval gate over every mutation in the app. Competitors stay in ADR-0008's "corrected freely, not audited" model; extending review to them was never asked for and would be scope creep.
4. **A queued write returns `202 Accepted` with a `ValidationQueueResponse`, not the normal `201`/`200` resource.** `POST`/`PUT /locations` now return a `LocationResponse | ValidationQueueResponse` union; the frontend distinguishes the two with a type guard (`isPendingReview`) rather than relying on the status code alone, since both shapes need to be handled wherever these calls are made (map add-prospect, rating edits, CSV import).
5. **Approval replays the change as the original submitter, not the reviewer.** `validation_service.approve()` calls `location_service.create_location`/`update_location` with `created_by`/`updated_by` set to `entry.submitted_by`, so `update_log` (ADR-0003/ADR-0006) attributes the eventual change to whoever actually proposed it, not whoever clicked Approve.
6. **CSV import rows skip the per-row rate-limit delay when queued.** A queued row has no geocode call yet (geocoding happens at `location_service.create_location` time, which only runs on approval), so there's nothing to throttle until then — `ImportResult` gained a `queued` count alongside `created`/`errors` so the summary stays honest about what actually happened to each row.
7. **Cross-org access returns 404, not 403.** `GET /validation-queue` is scoped to entries whose submitter belongs to the caller's organization; reusing an entry ID from another org 404s rather than 403s, consistent with the existing "don't leak existence" pattern used elsewhere in this project.

### Alternatives considered
- **Unconditional "non-admins are always queued" (no org-level toggle)**: rejected outright per the Context section — a real backward-compatibility break affecting every existing user, not a hypothetical one.
- **A role/permission-slug-based review requirement** (extending ADR-0012's unused `permissions`/`role_permissions` tables): rejected — this feature only ever needed a single boolean (admin bypasses, org opts in or out), not a granular per-capability system with nothing else in the app to hang off it yet.
- **Applying review to competitors and call notes too**: rejected — not requested, and would contradict ADR-0008's deliberate "competitors are corrected freely, not audited" design.
- **Returning normal `200`/`201` for a queued write with a `status: "pending"` field instead of a distinct `202` + different response shape**: rejected — a distinct status code and response shape makes "this didn't actually happen yet" impossible to miss in either the API contract or the frontend code, rather than relying on every caller to remember to check a field.

### Consequences
- Every current organization keeps today's behavior (writes apply immediately) until an admin deliberately opts in — verified by running the full existing test suite after each schema/behavior change with zero regressions.
- `POST`/`PUT /locations` callers (any future API consumer, not just this frontend) must handle a `202` union response, not just the success shape — documented in API.md.
- A queued update proposes a full replacement of only the changed fields (`exclude_none`), applied against whatever the location's state is *at approval time*, not at submission time — if the location was also edited directly by an admin in the meantime, the queued proposal could apply on top of a different base state than the submitter saw. No conflict detection is built for this edge case; acceptable for v1 given how narrow a window this requires, revisit if it proves to be a real problem.
- Rejecting a submission is terminal (no edit-and-resubmit flow) — the submitter would need to redo the submission from scratch. Acceptable for v1; a resubmit-with-edits flow is a natural but unscheduled follow-up.

---

## ADR-0015: Host businesses — search-or-create picker, no unlink, restrict-on-delete

Date: 2026-07-29
Status: Accepted

### Context
Phase 2, second item. `host_businesses` (the business hosting a vending machine — gas station, laundromat, ...) and `locations.host_business_id` were both designed and migrated in ADR-0003/the original Phase 1 migration, but nothing was ever built on top of them: no service, no routes, no way to create a host business or see its name/category anywhere in the product. `docs/DATABASE.md` had documented "Host Category" as a required Location attribute read via this FK since day one, but there was no way to actually set it.

### Decision
1. **Real CRUD for `host_businesses`** (`POST/GET/PUT/DELETE /host-businesses`, `GET` supporting `?search=` matching name or category), same shared-reference-data pattern as `competitors`/`brands` (ADR-0002) — no organization scoping.
2. **`LocationResponse` gains denormalized `host_business_name`/`host_business_category`**, populated via a lookup in `assemble_response`, matching the existing `state_code`/`county_name`/`city_name` pattern rather than nesting a full object — keeps this response shape consistent with how every other joined reference is already exposed.
3. **`host_business_id` is now validated on location create/update**, returning `422` with a clear message if the id doesn't exist, instead of letting a raw FK `IntegrityError` surface as an unhandled `500`. This is new rigor this feature specifically enables (there was no `host_business_service.get()` to validate against before); `brand_id` remains unvalidated for the same reason it always was — no `Brand` service exists yet, a separate, already-known gap (see Consequences).
4. **Frontend: search-or-create picker (`HostBusinessPicker`), not a rigid category dropdown or a separate management page.** Because `host_businesses` is a real normalized table (not free text), a location gets linked by searching existing rows first and falling back to a compact inline create form — mirrors the "find or add" shape this product already uses for competitor brand suggestions, and keeps `category` as free text with a `<datalist>` of examples (`gas_station`/`laundromat`/`grocery`/`convenience`) rather than a fixed enum, consistent with how `competitors.brand` is handled (ADR-0008 addendum). No standalone host-business directory/admin page was built — not requested, and the inline picker is sufficient for linking, which is the only operation the product currently needs.
5. **Deleting a host business still linked to a location is rejected (409), not cascaded.** `locations.host_business_id` has no `ON DELETE` behavior configured, so an unhandled delete would otherwise surface as a raw `IntegrityError`; silently nulling out every referencing location's field would also be an unrequested silent data change. The caller must actually resolve the reference first.
6. **No "unlink" affordance in v1.** Setting a location's `host_business_id` back to empty isn't supported by the location update endpoint's existing "only touch fields that are explicitly present, `None` means unset" convention — this is a pre-existing limitation of `LocationUpdateRequest`/`update_location` that already applied to every other optional field (e.g. `machine_type` can't be cleared once set either), not a new gap introduced by this feature. Not fixed here since it's out of this feature's scope; a real "clear this field" mechanism (e.g. a sentinel value or `PATCH`-with-explicit-null semantics) would need its own decision if it's ever needed broadly, not a one-off carve-out for host businesses.

### Alternatives considered
- **A fixed enum for `category`**: rejected — the schema's own documentation already described category as example values, not a closed set, and this product's established pattern (`competitors.brand`) is free text with suggestions, not a rigid enum.
- **Nesting a full `host_business` object in `LocationResponse`** instead of denormalized name/category fields: rejected for consistency — every other joined reference (`state_code`/`county_name`/`city_name`) is already flattened, and a location only ever needs the host business's display info, not its full record, in this context.
- **A standalone host-business list/management page**: rejected as unrequested scope — nothing today needs to browse host businesses independently of linking one to a location.
- **Cascading delete (nulling out referencing locations)**: rejected — silently clearing a location's host business as a side effect of an unrelated delete elsewhere is exactly the kind of silent data change this project avoids.

### Consequences
- `brand_id`'s lack of validation (no `Brand` CRUD/service exists) is now a visible inconsistency next to the newly-validated `host_business_id` — a pre-existing gap, not introduced here, but now more obviously worth a future pass if `brands` ever gets built out the same way.
- A location's host business, once linked, can only be *changed* to a different one, never cleared back to none, until a general "clear an optional field" mechanism is designed — a known, narrow limitation, not silent.
- 12 new backend tests (115 total) covering CRUD, search, the 409-in-use guard, and location integration (denormalized fields, 422 on invalid id); verified end-to-end in a real browser (search with no matches, inline create, persisted link confirmed via reload, 409 on deleting an in-use host business via curl).

---

## ADR-0016: Prospect quick-add gains competitor-equivalent fields; nested-form picker bug fixed

Date: 2026-07-29
Status: Accepted

### Context
User asked to add "the same fields for competitors" to the new-prospect card, so a prospect can be linked to a brand and given contact info at creation time instead of only afterward. `Location` and `Competitor` aren't the same shape, so this required deciding, field by field, what "the same" actually maps to, then building whatever didn't already exist. `brand_id` (designed in ADR-0002, migrated since Phase 1) had never been built on top of — no `Brand` service/routes, no frontend exposure anywhere — the exact same unbuilt-FK situation ADR-0015 had just fixed for `host_business_id`, flagged there as a known gap.

### Decision
1. **Field mapping, not a literal copy.** `competitors.brand` (free text) → the existing `brand_id` FK, finally wired up with a real `Brand` CRUD + search-or-create picker (`BrandPicker`), mirroring `HostBusinessPicker`/ADR-0015 exactly. `competitors.phone`/`contact_name` → the existing `primary_contact_phone`/`primary_contact_name` columns (already on `Location` since ADR-0006, never exposed in any form). `competitors.website`/`contact_email` → two new nullable columns, since `Location` had neither. `competitors.follow_up_at` → no new column; an initial `location_call_notes` row is created with that date immediately after save (reusing the mechanism `Location` already has for follow-ups, rather than adding a second, redundant date field). `competitors.name` was deliberately **not** added to `Location` — a prospect is already identified by its address, and `host_business_name` (ADR-0015) already covers "what business is here" when relevant; adding a second, separate name field would duplicate that.
2. **`Brand` CRUD built now, not deferred.** Same reasoning as ADR-0015's host-business build: the FK and migration already existed, only the service/routes/frontend were missing, and the user's request specifically included brand. New `POST/GET/PUT/DELETE /brands` (`GET ?search=`), `brand_service.py`, `BrandPicker.tsx` — structurally identical to the host-business build. Brands created through this picker are always shared/platform-wide (`organization_id` left null) even though the column supports a private, tenant-owned brand — nothing today needs the private path, and a franchise name isn't tenant-private data by nature.
3. **`AddProspectControl` switched from instant-create-on-click to click-then-fill-then-save**, matching `AddCompetitorControl`'s interaction exactly: clicking the map (or typing an address) no longer creates a location immediately — it stages a pending pin/address, and the same brand/website/contact/follow-up fields as the competitor form appear before an explicit "Save prospect". This is a real behavior change from ADR-0007's original "minimal, instant" design, made deliberately: showing fields "after placing the pin" is the literal ask, and it's not a backward-compatibility break (no stored data or API contract changes — `POST /locations` behaves identically either way; only the frontend's *when* changed).
4. **A follow-up note's `note_text` is a fixed, honest string** ("Follow-up scheduled when this prospect was added.") rather than an extra free-text field the user didn't ask for — `location_call_notes.note_text` is required, so something has to go there, and this describes exactly what happened rather than fabricating call content.
5. **Bug found and fixed while building this: nested `<form>` elements silently fail to submit in this app's target browser.** `BrandPicker`'s create-step form was rendered inside `AddProspectControl`'s own `<form>` — React explicitly warns about this ("cannot contain a nested form") and, empirically, clicking the inner submit button produced zero network activity and zero state change, not even a JS error. `event.stopPropagation()` was tried first and didn't fix it; the actual fix was removing the inner `<form>` entirely (a plain `<div>` with a `type="button"` + `onClick`, plus an `onKeyDown` Enter-to-submit handler on the text input to preserve the expected UX). Applied to `BrandPicker` (where it was live-broken) and `HostBusinessPicker` (same pattern, not currently nested in a form anywhere, but the identical latent risk) for consistency. **Any future picker/sub-form component must not use a `<form>` element if it might ever be embedded inside another form** — use a plain container with button `onClick` instead.

### Alternatives considered
- **Skipping brand entirely from the prospect quick-add** (treating it as out of scope, leaving `brand_id` unbuilt): rejected — the user explicitly asked for competitor-equivalent fields, and the incremental cost of reusing the just-built host-business pattern for brand was small.
- **Adding `follow_up_at` directly as a new `Location` column** instead of creating a call note: rejected — `Location` already has a complete, working follow-up mechanism (`location_call_notes` + calendar-link generation); a second date field would be redundant and inconsistent with how every existing prospect follow-up works.
- **Keeping instant-create-on-click and adding the new fields only to the post-create detail panel**: rejected — doesn't match "a card after placing the pin," and would leave prospects and competitors with divergent creation UX for no reason now that the fields line up.
- **`event.stopPropagation()` alone as the nested-form fix**: tried first, did not work — the browser's handling of a submit button whose nearest form ancestor is itself nested inside another form appears to suppress the submit before it becomes a normal bubbling event React can intercept, not merely double-fire two handlers. Removing the nested `<form>` was the only fix that actually worked.

### Consequences
- `Location` and `Competitor` now share contact-detail shape (name/phone via existing fields, website/email new) but remain intentionally distinct in others (`Competitor.name` required, `Location` has none; `Competitor.follow_up_at` a direct column, `Location`'s routed through call notes) — this is a considered mapping, not an oversight, documented here so it isn't "fixed" into false symmetry later.
- Any future compact create-form-with-a-sub-picker component (there will likely be more) must remember the nested-`<form>` constraint from day one — flagged in code comments in both picker components, not just here.
- 12 new backend tests (127 total) for brand CRUD and the new location fields; verified end-to-end in a real browser — brand search-or-create, all contact fields, and the follow-up-then-calendar-link flow all confirmed working via network log and a direct API fetch of the resulting location.
