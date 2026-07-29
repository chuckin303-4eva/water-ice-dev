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

## Identity & access (schema from ADR-0002, populated/enforced by ADR-0012)

**organizations** — a customer/tenant.
- `id` (PK), `name`, `require_review_for_submissions` (bool, default `false` — ADR-0014), `created_at`

**users**
- `id` (PK), `organization_id` (FK → organizations, indexed), `email` (unique), `hashed_password` (Argon2), `is_active`, `created_at`

**roles**
- `id` (PK), `organization_id` (FK, nullable for system-wide roles), `name`
- **Implemented** (ADR-0012): exactly two rows exist in practice, `"admin"` and `"member"`, both system-wide (`organization_id = NULL`), get-or-created lazily rather than seeded via a data migration.

**permissions**
- `id` (PK), `slug` (unique) — e.g. `location:read`, `report:export`
- **Still schema-only, unused** (ADR-0012) — no endpoint checks a fine-grained permission slug; role-based admin/member is what's actually enforced today. Revisit with a new ADR if/when a real capability needs finer-grained gating than "admin or not."

**role_permissions** — join table, unused (see `permissions` above).

**user_roles** — join table, **implemented**: every user created via registration or the Admin dashboard (ADR-0012) gets exactly one row here.

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

Modeled as site-level records — a specific observed rival machine at a specific address — since a location's Competition Score is computed from the density of nearby competitor rows, and the map needs competitor pins with real coordinates, not just a company name. **Implemented** (ADR-0008) — field set widened twice beyond the original design: `is_inside`/`machine_size`/`ice_price`/`water_price`/`price_notes` for the map's click-to-view panel, then `brand`/`website`/`phone`/`contact_name`/`contact_email`/`follow_up_at` for a compact manual-entry form (ADR-0008 addendum). Unlike `locations`, writes here don't go through `update_log` — that guarantee covers an operator's own prospecting history, not observations of rival machines, which are expected to be corrected freely as better information comes in.

**competitors**
- `id` (PK, UUID)
- `state_id`/`county_id`/`city_id` (FK, indexed), `address`
- `latitude`, `longitude` (indexed)
- `name` (the specific site's own name/label, required), `brand` (the parent franchise, e.g. "Twice the Ice" -- free text with UI autocomplete suggestions, not a link to the shared `brands` table)
- `website`, `phone`, `contact_name`, `contact_email`
- `follow_up_at` (nullable datetime) -- powers `GET /competitors/{id}/calendar-link` (Google/Outlook deep links, same `calendar_link_service` used by locations' call notes)
- `serves_ice` (bool), `serves_water` (bool), `machine_type`, `machine_size` — "size maybe"
- `is_inside` (bool, nullable) — same meaning as `locations.is_inside`
- `ice_price`, `water_price` (numeric, nullable), `price_notes` (free text — units/context vary by brand, e.g. "$1.75 per 16lb bag")
- `estimated_market_share`, `last_observed_date`, `source` (free text — how this row was populated, e.g. "manual field observation", a URL, or a future provider name), `notes`
- `created_at`, `updated_at`
- No free, automated, nationwide source exists for specific ice/water vending machine addresses (confirmed by research, ADR-0008) — major brands' locators require their mobile apps or a zip-code-driven interactive map, not a scrapeable static list, and OSM has essentially no coverage for this niche. Every row here is either entered by hand (an operator's own market knowledge, most reliable for this niche) or, later, a paid-API/Market-Refresh write — same honesty pattern as the deferred utility lookups in ADR-0006.

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
- `visibility_rating` — **Implemented** (ADR-0009). Manually-entered 1-10 rating, exposed via the API for the first time by Basic Scoring.
- `traffic_score` — **Implemented** (ADR-0009). Manually-entered 1-10 rating (redefined from its original "foot/vehicle traffic estimate" description — no traffic-data API exists or is designed, so a defined manual scale was chosen instead of an undefined "estimate").
- `population` — surrounding population figure. **Still unused** — no free demographic data source is wired (Market Refresh Engine, ADR-0004, Phase 3); deliberately excluded from the opportunity_score formula, not defaulted to zero.
- `median_income` — "Income". Same status as `population`.
- `growth_rate` — "Growth". Same status as `population`.
- `competition_score` — **Implemented** (ADR-0009). Real-time distance-weighted density of nearby `competitors` rows (app-level haversine, no PostGIS per ADR-0002), snapshotted at last calculation.
- `opportunity_score` — **Implemented** (ADR-0009). Composite of `visibility_rating` + `traffic_score` + `competition_score`; `null` until both manual ratings are set (no default-guessing).
- `confidence_score` — **Implemented** (ADR-0009). Reflects how many of the two manual ratings are present (0/50/100), not the site's actual quality.
- `status` (e.g. `prospect`, `active`, `inactive`, `lost`, `competitor_occupied`)
- `created_at`, `updated_at` (auto-managed)
- `last_verified_at`, `verification_source`
- `notes`

Not organization-scoped: per ADR-0002, location/market data is shared platform-wide intelligence, not a single tenant's private data. Pursuit of a specific location by a specific organization lives in `opportunities`, not on `locations` itself.

**Prospecting fields (ADR-0006)** — all manually entered unless noted; see ADR-0006 for exactly what is/isn't automatable and why:
- `property_owner_name`, `property_owner_phone`
- `property_management_company`, `property_management_contact_name`, `property_management_contact_phone`
- `primary_contact_name`, `primary_contact_phone`
- `expected_unit_size` — free text (e.g. "10x10 ft")
- `power_connection_location`, `power_company`, `power_voltage` — power company auto-lookup designed (EIA + OpenEI URDB, both free) but not built yet
- `water_connection_location`, `water_company` — water company auto-lookup designed (EPA service-area dataset, free) but not built yet
- `sewer_connection_availability`, `sewer_connection_location` — no automatable source found; stays manual indefinitely
- `pricing_estimate_monthly`, `pricing_estimate_notes`

Property ownership fields above stay manual indefinitely too — confirmed no free nationwide parcel-ownership API exists (ADR-0006).

## Location call notes

**location_call_notes** — a log of prospecting calls, append-only (never edited/deleted).
- `id` (PK), `location_id` (FK → locations, indexed), `note_text`, `call_date`, `follow_up_at` (nullable, indexed — when set, this is what a calendar-link endpoint turns into a Google Calendar/Outlook event), `created_by` (FK → users), `created_at`

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
- **Implemented** (ADR-0014) — currently the only writer is the Phase 2 validation workflow: `POST /locations`, `PUT /locations/{id}`, and per-row `POST /locations/import` land here instead of applying directly when the submitter's organization has `require_review_for_submissions = true` and the submitter isn't an admin. `entity_id = NULL` means "propose a new location"; `entity_id` set means "propose changes to this existing location," with `proposed_changes` holding only the changed fields. Approving a queued entry replays the create/update as the original submitter (so `update_log` attributes it correctly), not as the reviewer. The Market Refresh Engine's planned use (ADR-0004) is not yet built.

**update_log** — the append-only audit trail described above. **Implemented** (ADR-0006) — the first real writer is `locations` create/update/archive.
- `id` (PK), `entity_type`, `entity_id` (text — holds the string form of whatever PK type the entity uses), `field_name`, `old_value`, `new_value`, `changed_by` (FK → users, nullable — null for system changes), `change_source` (`manual`/`import`/`system`/`verification`), `changed_at`
- Indexed on `entity_type`, `entity_id`, and `changed_at` for chronological queries.

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
