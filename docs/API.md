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
