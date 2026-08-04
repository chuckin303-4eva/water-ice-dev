# API

REST, JSON request/response bodies. No versioning scheme yet — revisit
once there's a second consumer that needs backward compatibility (no
public API exists per [ROADMAP.md](ROADMAP.md); premature to version
against nobody).

## Authentication

JWT bearer tokens (see [ARCHITECTURE.md](ARCHITECTURE.md) and
[SECURITY.md](SECURITY.md)):

- `POST /auth/login` with email/password returns an access token (30 min
  default expiry) and a refresh token (7 days default expiry).
- Protected endpoints require `Authorization: Bearer <access_token>`.
- `POST /auth/refresh` exchanges a valid refresh token for a new access
  token. Refresh tokens are **not** rotated on use and are **not**
  revocable before their natural expiry — no server-side revocation list
  exists yet (accepted trade-off, see docs/SECURITY.md).
- `POST /auth/register` (ADR-0012) creates a brand-new organization plus
  its first user (that org's admin) and logs them in immediately. No
  email verification or CAPTCHA -- deferred, not silently faked.
- Two system-wide roles exist, `"admin"` and `"member"` (ADR-0012) --
  `GET /auth/me` and every `/organizations/users` response include the
  caller's/target's `role`. Only admins can create or modify other users
  in their organization; any authenticated user can list their own
  organization's roster.
- **Validation workflow (ADR-0014)**: if an organization has
  `require_review_for_submissions` turned on (`PUT /organizations/settings`,
  admin only), a non-admin's `POST`/`PUT /locations` (and each row of
  `POST /locations/import`) is queued for approval instead of applying
  immediately -- the response is `202 Accepted` with a
  `ValidationQueueResponse` body instead of the normal
  `LocationResponse`/`201`/`200`. Admin writes always apply directly,
  regardless of this setting. Default is off for every organization.

## Endpoints

| Method | Path | Description | Auth required |
|---|---|---|---|
| GET | `/health` | Liveness check | No |
| POST | `/auth/register` | Create a new organization + its first (admin) user, and log them in | No |
| POST | `/auth/login` | Exchange email+password for access+refresh tokens | No |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token | No (refresh token in body) |
| GET | `/auth/me` | Return the authenticated user, including `role` | Yes |
| GET | `/organizations/users` | List your organization's users (id, email, is_active, role, created_at) | Yes |
| POST | `/organizations/users` | Create a teammate in your organization (admin only). Sets a real password directly -- no email is sent, there's no email service (ADR-0012) | Yes (admin) |
| PUT | `/organizations/users/{user_id}` | Update a teammate's `is_active` and/or `role` (admin only). Rejects modifying your own account (400) | Yes (admin) |
| GET | `/organizations/settings` | Get `{require_review_for_submissions}` for your organization (ADR-0014) | Yes |
| PUT | `/organizations/settings` | Set `require_review_for_submissions` for your organization (admin only) | Yes (admin) |
| GET | `/validation-queue` | List your organization's queued submissions, plus every system-sourced entry (no submitting user, e.g. from Market Refresh -- ADR-0020) since those concern shared platform-wide location data, not one tenant's private submission. `?status_filter=pending` by default; pass `status_filter=` (empty) or another status to see approved/rejected entries too (ADR-0014) | Yes (admin) |
| POST | `/validation-queue/{id}/approve` | Approve a queued submission -- applies it (as the original submitter, for `update_log` attribution; `change_source="verification"` instead of `"manual"` for a system-sourced entry) and returns the resulting `LocationResponse`. 409 if already reviewed | Yes (admin) |
| POST | `/validation-queue/{id}/reject` | Reject a queued submission with an optional `reason`. 409 if already reviewed | Yes (admin) |
| POST | `/host-businesses` | Create a host business (name required; category/phone/website optional) (ADR-0015) | Yes |
| GET | `/host-businesses` | List host businesses. `?search=` matches name or category, case-insensitive partial -- powers the location detail panel's search-or-create picker | Yes |
| GET | `/host-businesses/{id}` | Get a host business | Yes |
| PUT | `/host-businesses/{id}` | Update a host business (partial) | Yes |
| DELETE | `/host-businesses/{id}` | Delete a host business. 409 if any location still references it | Yes |
| POST | `/brands` | Create a brand (name required; description/logo_url optional). Always shared/platform-wide (ADR-0016) | Yes |
| GET | `/brands` | List brands. `?search=` matches name -- powers the Add Prospect card's search-or-create picker | Yes |
| GET | `/brands/{id}` | Get a brand | Yes |
| PUT | `/brands/{id}` | Update a brand (partial) | Yes |
| DELETE | `/brands/{id}` | Delete a brand. 409 if any location still references it | Yes |
| POST | `/locations` | Create a location/prospect. Requires `address`, or `latitude`+`longitude`, or both -- whichever is missing is filled in by geocoding (Nominatim). Returns `202` + `ValidationQueueResponse` instead of `201` + `LocationResponse` if the org requires review and the caller isn't an admin (ADR-0014). `host_business_id`/`brand_id`, if given, must reference an existing row (422 otherwise, ADR-0015/ADR-0016). Also accepts `website`, `primary_contact_name`, `primary_contact_phone`, `primary_contact_email` (ADR-0016) | Yes |
| GET | `/locations` | List locations. Filters (ADR-0010): `?statuses=` (repeatable, e.g. `statuses=prospect&statuses=active`), `?serves_ice=true`, `?serves_water=true` (opt-in narrowing -- OR across whichever are set, omitted means no filter), `?min_opportunity_score=` | Yes |
| POST | `/locations/import` | Bulk-create locations from a CSV file (`multipart/form-data`, field name `file`). Columns: `address` (or `latitude`+`longitude`), `serves_ice`, `serves_water`, `notes`. Max 100 rows per file (422 if exceeded); partial success -- returns `{total_rows, created, queued, errors: [{row, message}]}`, one row's failure doesn't block the rest (ADR-0011). `queued` counts rows sent to the review queue instead of created directly (ADR-0014) | Yes |
| GET | `/locations/export` | Download all locations matching the same filters as `GET /locations` as a CSV file, full field set (not just the import columns) (ADR-0013) | Yes |
| GET | `/locations/{id}` | Get a location | Yes |
| PUT | `/locations/{id}` | Update a location (partial; logs every changed field to `update_log`). Setting `visibility_rating`/`traffic_score` (1-10 each) triggers score recalculation (ADR-0009). Returns `202` + `ValidationQueueResponse` instead of `200` + `LocationResponse` if the org requires review and the caller isn't an admin (ADR-0014) | Yes |
| DELETE | `/locations/{id}` | Archive a location (soft delete, status -> `archived`) | Yes |
| POST | `/locations/{id}/call-notes` | Add a prospecting call note, optional `follow_up_at` | Yes |
| GET | `/locations/{id}/call-notes` | List call notes for a location | Yes |
| GET | `/locations/{id}/call-notes/{note_id}/calendar-link` | Google Calendar + Outlook "add event" links for a note's `follow_up_at`. 409 if the note has no follow-up date | Yes |
| POST | `/locations/{id}/recalculate-score` | Recompute `competition_score`/`opportunity_score`/`confidence_score` without changing any other field -- for any residual case not already covered by the automatic recalculation below (ADR-0017) | Yes |
| POST | `/competitors` | Create a competitor. Requires `name` plus `address`, or `latitude`+`longitude`, or both. Also recalculates scores for every location within 10 miles (ADR-0017) | Yes |
| GET | `/competitors` | List competitors. Filters (ADR-0010): `?serves_ice=true`, `?serves_water=true` (same opt-in OR semantics as locations), `?brand=` (case-insensitive partial match) | Yes |
| GET | `/competitors/export` | Download all competitors matching the same filters as `GET /competitors` as a CSV file, full field set (ADR-0013) | Yes |
| GET | `/competitors/{id}` | Get a competitor | Yes |
| PUT | `/competitors/{id}` | Update a competitor (partial; no `update_log` -- see docs/DATABASE.md). Also recalculates scores for locations within 10 miles of both the old and new position (ADR-0017) | Yes |
| DELETE | `/competitors/{id}` | Permanently remove a competitor (hard delete, unlike locations' archive -- these are corrected/replaced freely, not an audited history). Also recalculates scores for every location within 10 miles (ADR-0017) | Yes |
| GET | `/competitors/{id}/calendar-link` | Google Calendar + Outlook "add event" links for the competitor's `follow_up_at`. 409 if no follow-up date is set | Yes |
| POST | `/locations/{id}/photos` | Upload a photo (`multipart/form-data`: `file`, optional `caption`, `is_primary`). Compressed and content-type-verified via Pillow; 422 if not a real image, wrong type, or over the 10 MB limit (ADR-0018) | Yes |
| GET | `/locations/{id}/photos` | List a location's photos, primary first | Yes |
| DELETE | `/locations/{id}/photos/{photo_id}` | Delete a photo (row + file) | Yes |
| POST | `/competitors/{id}/photos` | Same as the location version, for a competitor (ADR-0018) | Yes |
| GET | `/competitors/{id}/photos` | List a competitor's photos, primary first | Yes |
| DELETE | `/competitors/{id}/photos/{photo_id}` | Delete a photo (row + file) | Yes |
| GET | `/media/{entity_type}/{filename}` | Serves an uploaded photo. **Not authenticated** -- protected only by the unguessable UUID filename (ADR-0018) | No |
| GET | `/billing/plans` | List the pricing catalog (`free`/`starter`/`pro`) -- a fixed list in code, not a database table (ADR-0019) | Yes |
| GET | `/billing/subscription` | Get your organization's current effective plan/status. Returns the free plan implicitly if no subscription row exists | Yes |
| POST | `/billing/subscribe` | Subscribe or switch to a paid plan (`{plan_slug}`). Backed by a mock provider -- no real payment is collected. 422 for an unknown plan or `plan_slug: "free"` (use cancel instead) | Yes (admin) |
| POST | `/billing/cancel` | Cancel the current paid subscription immediately, reverting to the free plan. 409 if nothing is active | Yes (admin) |
| GET | `/billing/invoices` | List billing history for your organization, newest first (ADR-0019) | Yes (admin) |
| POST | `/market-refresh/runs` | Trigger a Market Refresh run: re-checks up to 20 locations (oldest/never-checked first) against OpenStreetMap (address drift) and US Census (demographics), queuing one combined `validation_queue` proposal per location with any drift. Synchronous -- can take up to ~a minute. Never writes to `locations` directly (ADR-0020) | Yes (admin) |
| GET | `/market-refresh/runs` | List past refresh runs, newest first | Yes (admin) |
| POST | `/opportunities` | Start pursuing a location (`{location_id, stage?}`, default stage `identified`). 422 for an unknown location, an invalid stage, or an `assigned_user_id` outside your organization (ADR-0021) | Yes |
| GET | `/opportunities` | List your organization's pursuits (`?stage=`, `?location_id=` both optional filters) | Yes |
| GET | `/opportunities/{id}` | Get one pursuit. 404 outside your organization | Yes |
| PUT | `/opportunities/{id}` | Update stage/assignee/priority/target date/notes. 404 outside your organization, 422 for an invalid stage/assignee | Yes |
| DELETE | `/opportunities/{id}` | Stop tracking a pursuit (hard delete -- unlike locations, there's no audit requirement on abandoning a pursuit) | Yes |
| GET | `/analytics/summary` | Portfolio-wide location/competitor/demographic aggregates (status breakdown, score distribution, top prospects, growth markets from ADR-0020's demographics, most-contested markets) plus your organization's own pursuit-pipeline funnel (ADR-0021) | Yes |

`PUT /locations/{id}` also accepts `population`/`median_income`/`growth_rate` (ADR-0020) -- these exist for the Market Refresh Engine's approved proposals to write through; no manual-entry UI prompts for them today, though a human could still set them directly via this endpoint.

Unlike locations/competitors, `opportunities` **is** organization-scoped (ADR-0021) -- it tracks one organization's specific pursuit of a location, not the shared location data itself.

Locations and competitors are not organization-scoped (ADR-0002: shared market intelligence, not per-tenant private data) -- any authenticated user can create/view/edit either.
