# Database

PostgreSQL. Full schema, organized by domain, per ADR-0001/ADR-0002/ADR-0003 in [DECISIONS.md](DECISIONS.md).

## Migration policy (in force now)

- Every schema change ships as a versioned Alembic migration, never a manual/ad-hoc change against any environment.
- No destructive migration (dropped column/table, irreversible transform, type narrowing that loses data) merges without a reviewed rollback path and a verified backup immediately before it runs in production.
- Migrations run in the same order in every environment (local, staging, production) — no environment-specific drift.
- Adding indexes on large tables uses `CREATE INDEX CONCURRENTLY` to avoid locking `locations` at 100,000+ rows.
- Each industry module owns migrations for its own tables; core migrations never depend on a module existing.

## History policy: never overwrite, always log

Core mutable tables (especially `locations`) are updated in place for current-state reads — but every UPDATE to a tracked table also writes one row per changed field to `update_log`, in the same transaction. `update_log` is append-only and is the historical record; nothing is ever deleted from it. This gives full change history without turning every table into a versioned/temporal table, which would be overbuilt for data that's mostly append-then-refine rather than branching/versioned. **This interpretation of "never overwrite historical information" is worth confirming** — the alternative is full row-versioning (every update inserts a new row instead of updating), which is heavier but preserves complete point-in-time snapshots, not just field-level diffs.

## Identity & access (from ADR-0002, unchanged)

**organizations** — a customer/tenant.
- `id` (PK), `name`, `created_at`

**users**
- `id` (PK), `organization_id` (FK → organizations, indexed), `email` (unique), `hashed_password` (Argon2), `is_active`, `created_at`

**roles**
- `id` (PK), `organization_id` (FK, nullable for system-wide roles), `name`

**permissions**
- `id` (PK), `slug` (unique) — e.g. `location:read`, `report:export`

**role_permissions** / **user_roles** — join tables, unchanged.

**resource_listings** / **resource_listing_responses** — cross-tenant resource pooling, unchanged from ADR-0002.

## Geography (new)

Normalized state → county → city hierarchy, referenced by `locations` and `competitors`.

**states**
- `id` (PK), `code` (2-letter, unique), `name`

**counties**
- `id` (PK), `state_id` (FK → states, indexed), `fips_code` (unique, nullable), `name`
- Unique on `(state_id, name)`.

**cities**
- `id` (PK), `state_id` (FK → states, indexed), `county_id` (FK → counties, indexed, nullable), `name`
- Simplification: a city is stored under one primary county even though real-world city boundaries occasionally span counties. Not modeling a city↔county many-to-many unless a real case forces it (YAGNI) — flag if you know this matters for target markets.

ZIP code is **not** a normalized table — it's a plain indexed column on `locations`. ZIP boundaries don't nest cleanly inside city/county boundaries in the real world, so treating ZIP as a child of city would misrepresent actual geography.

## Brands

**brands** — a vending brand/franchise a location operates under.
- `id` (PK, UUID), `organization_id` (FK → organizations, nullable — null means a shared/reference brand visible platform-wide, set means a tenant's own private brand), `name`, `description`, `logo_url`, `created_at`, `updated_at`

## Host businesses

**host_businesses** — the business hosting a vending machine at a location (gas station, laundromat, grocery store, ...).
- `id` (PK, UUID), `name`, `category` (e.g. `gas_station`, `laundromat`, `grocery`, `convenience`), `phone`, `website`, `created_at`, `updated_at`
- "Host Category" (a required Location attribute) is read via `locations.host_business_id → host_businesses.category`, not duplicated as a column on `locations` — avoids storing the same fact twice.

## Competitors

Modeled as site-level records — a specific observed rival machine at a specific address — since a location's Competition Score is computed from the density of nearby competitor rows, and the map needs competitor pins with real coordinates, not just a company name.

**competitors**
- `id` (PK, UUID), `name` (rival brand/operator), `state_id`/`county_id`/`city_id` (FK, indexed), `address`, `latitude`, `longitude` (indexed), `serves_ice` (bool), `serves_water` (bool), `machine_type`, `estimated_market_share`, `last_observed_date`, `source`, `notes`, `created_at`, `updated_at`

## Locations — the central table

`serves_ice`/`serves_water`/`machine_type` live directly on `locations` (ADR-0003): ice and water vending are the entire product today, so these are core columns rather than per-module extension tables. A genuinely new third industry later would require a migration to split product-specific fields out of core — an accepted, deferred cost, not a current problem.

**locations**
- `id` (PK, **UUID**, server-generated, immutable) — "Permanent UUID" per your requirement
- `state_id` (FK → states, indexed)
- `county_id` (FK → counties, indexed)
- `city_id` (FK → cities, indexed)
- `zip_code` (indexed)
- `address`
- `latitude`, `longitude` (numeric, indexed — plain lat/lng per ADR-0002, no PostGIS)
- `brand_id` (FK → brands, nullable, indexed)
- `serves_ice` (bool), `serves_water` (bool) — together express "Ice / Water / Both" as two flags rather than a three-way enum, so "which locations serve ice" is a plain boolean filter and adding a third product later doesn't mean widening an enum
- `machine_type`
- `host_business_id` (FK → host_businesses, nullable, indexed)
- `is_inside` (bool) — "Inside/Outside"
- `visibility_rating` — visibility of the machine at the site
- `traffic_score` — foot/vehicle traffic estimate
- `population` — surrounding population figure
- `median_income` — "Income"
- `growth_rate` — "Growth"
- `competition_score` — derived/computed, snapshotted at last calculation
- `opportunity_score` — derived/computed, snapshotted at last calculation
- `confidence_score` — confidence in the data backing this record's scores
- `status` (e.g. `prospect`, `active`, `inactive`, `lost`, `competitor_occupied`)
- `created_at`, `updated_at` (auto-managed)
- `last_verified_at`, `verification_source`
- `notes`

Not organization-scoped: per ADR-0002, location/market data is shared platform-wide intelligence, not a single tenant's private data. Pursuit of a specific location by a specific organization lives in `opportunities`, not on `locations` itself.

## Opportunities

A location's `opportunity_score` is a computed metric; `opportunities` is the human workflow layer on top of it — tracking who is actually pursuing a given location and how far along they are. Keeping these separate avoids conflating "how good is this site, generically" with "what's the status of our specific pursuit of it."

**opportunities**
- `id` (PK), `location_id` (FK → locations, indexed), `organization_id` (FK → organizations, indexed — who's pursuing it), `stage` (`identified`/`contacted`/`negotiating`/`won`/`lost`), `assigned_user_id` (FK → users, nullable), `priority`, `target_action_date`, `outcome_notes`, `created_at`, `updated_at`

## Attachments: Photos, Documents, Reviews

These attach to more than one entity type (a location, a host business, a competitor sighting), so they use a polymorphic `entity_type` + `entity_id` pair rather than a separate table per parent. This is the one deliberate exception to "no generic/polymorphic references" in this schema — scoped to attachment/workflow tables, not core domain data.

`locations`, `host_businesses`, `competitors`, and `brands` all use UUID primary keys (ADR-0003), so `entity_id` here is always a UUID regardless of which of the four it points to — no per-entity-type casting needed.

**photos**
- `id` (PK), `entity_type`, `entity_id`, `file_key`, `caption`, `uploaded_by` (FK → users), `uploaded_at`, `is_primary` (bool)

**documents**
- `id` (PK), `entity_type`, `entity_id`, `document_type` (`contract`/`permit`/`verification`/`other`), `file_key`, `organization_id` (FK, nullable — set when the document is a specific tenant's private paperwork, e.g. a host agreement, rather than shared reference material), `uploaded_by`, `uploaded_at`, `notes`

**reviews**
- `id` (PK), `entity_type`, `entity_id`, `source` (`google`/`yelp`/`internal`/`operator`), `rating`, `review_text`, `review_date`, `author_name`, `created_at`

Indexed on `(entity_type, entity_id)` in all three.

## Workflow & audit

**validation_queue** — records awaiting human review before their data is trusted (newly scraped/imported locations, proposed edits, etc.).
- `id` (PK), `entity_type`, `entity_id`, `proposed_changes` (JSONB — the specific field/value pairs awaiting approval), `reason`, `submitted_by` (FK → users, nullable — null for system/import submissions), `status` (`pending`/`approved`/`rejected`), `reviewed_by` (FK → users, nullable), `reviewed_at`, `created_at`

**update_log** — the append-only audit trail described above.
- `id` (PK), `entity_type`, `entity_id`, `field_name`, `old_value`, `new_value`, `changed_by` (FK → users, nullable — null for system changes), `change_source` (`manual`/`import`/`system`/`verification`), `changed_at`
- Indexed on `(entity_type, entity_id)` and on `changed_at` for chronological queries.

**tasks**
- `id` (PK), `title`, `description`, `organization_id` (FK → organizations, indexed), `assigned_user_id` (FK → users, nullable), `related_entity_type` (nullable), `related_entity_id` (nullable), `status` (`open`/`in_progress`/`done`/`cancelled`), `priority`, `due_date`, `created_by` (FK → users), `created_at`, `updated_at`

**settings**
- `id` (PK), `organization_id` (FK, nullable — null is a global/system default, set is a tenant override), `key`, `value` (JSONB), `description`, `updated_by` (FK → users), `updated_at`
- Unique on `(organization_id, key)`.

## Market refresh

**refresh_runs** — one row per "Refresh Market" invocation (ADR-0004).
- `id` (PK), `started_at`, `completed_at` (nullable), `status` (`running`/`completed`/`failed`), `triggered_by` (FK → users, nullable — null for a future scheduled run, always set for v1's manual button), `locations_reviewed`, `changes_queued`, `providers_used` (JSONB list of provider slugs actually run), `error_message` (nullable)

A refresh run never writes to `locations` directly — it only creates `validation_queue` entries. `validation_queue.entity_type`/`entity_id` point at the affected `locations`/`competitors` row (or, for duplicate detection, `entity_type = "location_duplicate"` with the candidate duplicate's id inside `proposed_changes`). Approving a queue entry is what writes to `locations` and to `update_log`, per [ARCHITECTURE.md](ARCHITECTURE.md#market-refresh-engine-adr-0004).

## Indexing plan

- All FK columns listed above are indexed.
- `locations`: `state_id`, `county_id`, `city_id`, `zip_code`, `brand_id`, `host_business_id`, `status`, `latitude`, `longitude`.
- `competitors`: `state_id`, `county_id`, `city_id`, `latitude`, `longitude`.
- `users.email`: unique index.
- `(entity_type, entity_id)` composite index on `photos`, `documents`, `reviews`, `validation_queue`, `update_log`.
- `(organization_id, ...)` composite indexes on tenant-scoped list-view tables (`tasks`, `opportunities`, `settings`) to keep pagination fast per tenant.

## Avoiding duplicate data

- Geography (state/county/city name and code) is normalized once and referenced by FK from `locations`/`competitors`, never repeated as free-text columns.
- Host category comes from `host_businesses.category` via FK, not duplicated onto `locations`.
- A location's identity (address, coordinates) lives once in `locations`; attachments and workflow tables reference it by `entity_id`, they don't copy its data.
