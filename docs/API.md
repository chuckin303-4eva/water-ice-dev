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
- There is no self-serve registration endpoint. Until the Admin dashboard
  (Phase 1, item 8) exists, the first user in an organization is created
  via `backend/scripts/seed_dev_user.py`.

## Endpoints

| Method | Path | Description | Auth required |
|---|---|---|---|
| GET | `/health` | Liveness check | No |
| POST | `/auth/login` | Exchange email+password for access+refresh tokens | No |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token | No (refresh token in body) |
| GET | `/auth/me` | Return the authenticated user | Yes |
| POST | `/locations` | Create a location/prospect. Requires `address`, or `latitude`+`longitude`, or both -- whichever is missing is filled in by geocoding (Nominatim) | Yes |
| GET | `/locations` | List locations. Filters (ADR-0010): `?statuses=` (repeatable, e.g. `statuses=prospect&statuses=active`), `?serves_ice=true`, `?serves_water=true` (opt-in narrowing -- OR across whichever are set, omitted means no filter), `?min_opportunity_score=` | Yes |
| GET | `/locations/{id}` | Get a location | Yes |
| PUT | `/locations/{id}` | Update a location (partial; logs every changed field to `update_log`). Setting `visibility_rating`/`traffic_score` (1-10 each) triggers score recalculation (ADR-0009) | Yes |
| DELETE | `/locations/{id}` | Archive a location (soft delete, status -> `archived`) | Yes |
| POST | `/locations/{id}/call-notes` | Add a prospecting call note, optional `follow_up_at` | Yes |
| GET | `/locations/{id}/call-notes` | List call notes for a location | Yes |
| GET | `/locations/{id}/call-notes/{note_id}/calendar-link` | Google Calendar + Outlook "add event" links for a note's `follow_up_at`. 409 if the note has no follow-up date | Yes |
| POST | `/locations/{id}/recalculate-score` | Recompute `competition_score`/`opportunity_score`/`confidence_score` without changing any other field -- for when nearby `competitors` data changed instead of the location itself | Yes |
| POST | `/competitors` | Create a competitor. Requires `name` plus `address`, or `latitude`+`longitude`, or both | Yes |
| GET | `/competitors` | List competitors. Filters (ADR-0010): `?serves_ice=true`, `?serves_water=true` (same opt-in OR semantics as locations), `?brand=` (case-insensitive partial match) | Yes |
| GET | `/competitors/{id}` | Get a competitor | Yes |
| PUT | `/competitors/{id}` | Update a competitor (partial; no `update_log` -- see docs/DATABASE.md) | Yes |
| DELETE | `/competitors/{id}` | Permanently remove a competitor (hard delete, unlike locations' archive -- these are corrected/replaced freely, not an audited history) | Yes |
| GET | `/competitors/{id}/calendar-link` | Google Calendar + Outlook "add event" links for the competitor's `follow_up_at`. 409 if no follow-up date is set | Yes |

Locations and competitors are not organization-scoped (ADR-0002: shared market intelligence, not per-tenant private data) -- any authenticated user can create/view/edit either.
