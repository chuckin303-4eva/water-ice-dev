# Database

PostgreSQL. Schema below is a proposed starting point for the core (industry-independent) tables — pending sign-off in [ARCHITECTURE.md](ARCHITECTURE.md#open-decisions-need-your-sign-off-before-scaffolding) on PostGIS and the multi-tenancy model. Industry modules (ice vending, water vending, ...) add their own tables with a foreign key back to `locations`/`businesses`; they do not modify core tables.

## Migration policy (in force now)

- Every schema change ships as a versioned Alembic migration, never a manual/ad-hoc change against any environment.
- No destructive migration (dropped column/table, irreversible transform, type narrowing that loses data) merges without a reviewed rollback path and a verified backup immediately before it runs in production.
- Migrations run in the same order in every environment (local, staging, production) — no environment-specific schema drift.
- Every migration is reviewed for lock behavior on the target database before it runs against production-scale data (relevant here: adding indexes on a 100,000+ row table should use `CREATE INDEX CONCURRENTLY`).
- Each industry module owns migrations for its own tables; core migrations never depend on a module existing.

## Proposed core schema (pending sign-off)

**organizations** — a customer/tenant.
- `id` (PK), `name`, `created_at`

**users**
- `id` (PK), `organization_id` (FK → organizations, indexed), `email` (unique), `hashed_password` (Argon2), `is_active`, `created_at`

**roles**
- `id` (PK), `organization_id` (FK, nullable for system-wide roles), `name`

**permissions**
- `id` (PK), `slug` (unique) — e.g. `location:read`, `report:export`

**role_permissions** (join table)
- `role_id` (FK), `permission_id` (FK)

**user_roles** (join table)
- `user_id` (FK), `role_id` (FK)

**locations** — industry-agnostic physical location.
- `id` (PK), `name`, `address`, `city`, `state`, `postal_code`
- `geom` (PostGIS `GEOGRAPHY(Point)`, GiST-indexed) — pending PostGIS approval; interim fallback is `latitude`/`longitude` numeric columns with a plain b-tree index, which does not support radius/nearest queries efficiently
- `location_type` (enum: e.g. `retail`, `gas_station`, `laundromat`, ...)
- `created_at`, `updated_at`

**businesses** — an operator or host business entity.
- `id` (PK), `name`, `business_type` (enum: `vending_operator`, `host`, `competitor`, ...)
- `organization_id` (FK, nullable — null for businesses that are just market data, set when the business *is* a platform customer)

**business_locations** (join table — a business can operate at/relate to multiple locations)
- `business_id` (FK), `location_id` (FK), `relationship_type` (e.g. `operates`, `hosts`, `competes_at`)

## Per-module tables (example: ice_vending)

**ice_vending_profiles**
- `id` (PK), `location_id` (FK → locations, unique — one profile per location), `machine_type`, `capacity_lbs`, `installed_at`, module-specific scoring inputs as explicit typed columns (not JSONB) so they stay queryable and indexable.

Water vending and future industries follow the same pattern: a `<module>_profiles` table (or several, if the domain needs more than one) keyed by `location_id`.

## Indexing plan

- FK columns: `users.organization_id`, `business_locations.business_id`, `business_locations.location_id`, `<module>_profiles.location_id` — all indexed.
- `locations.geom`: GiST spatial index (pending PostGIS) for radius/nearest-neighbor queries at 100,000+ rows.
- `users.email`: unique index.
- Composite index on `(organization_id, ...)` for any table queried per-tenant in list views, to keep tenant-scoped pagination fast.

## Avoiding duplicate data

- Location and business identity live once in `locations`/`businesses`; every module references them by FK rather than copying name/address/coordinates into module tables.
- Shared lookup values (location types, business types, relationship types) are enums or small reference tables, not repeated strings.
