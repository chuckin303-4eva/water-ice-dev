# Security Policy

## Secrets handling

- No secrets, API keys, tokens, passwords, or credentials are ever committed to this repository — including in code, config files, comments, commit messages, or test fixtures.
- Local configuration lives in `.env` (git-ignored). A `.env.example` with placeholder values and comments must be kept up to date whenever a new required variable is introduced.
- If a secret is accidentally committed: rotate it immediately (assume it is compromised the moment it hits a commit, even if the commit is later removed — git history and forks can retain it), then scrub it from history.
- Production/staging secrets are managed via the hosting platform's secret manager once one is chosen (see [DEPLOYMENT.md](DEPLOYMENT.md)) — never passed via plaintext config in the repo.

## Dependency policy

- New dependencies require a stated justification (see [CODING_STANDARDS.md](CODING_STANDARDS.md)).
- Dependencies are checked for known vulnerabilities before every commit as tooling is wired in (see [CODING_STANDARDS.md](CODING_STANDARDS.md) pre-commit checks).
- Prefer well-maintained, widely-used packages over novel or unmaintained ones. Fewer dependencies is a security property, not just a convenience one.

## Authentication

- Passwords hashed with Argon2 (`argon2-cffi`), never stored or logged in plaintext.
- JWT access tokens (30 min default) and refresh tokens (7 day default), signed with `SECRET_KEY` (HS256).
- **Known accepted risk:** refresh tokens are stateless -- there is no server-side revocation list. A stolen refresh token remains valid until it naturally expires; there is no way to force-logout a user or invalidate a specific token early. Mitigated for now by keeping the expiry short. Revisit with a DB-backed revocation table (e.g. a `refresh_tokens` table with a `revoked` flag) if/when this risk needs closing -- record that as a new ADR when it happens, don't add it silently.
- No self-serve registration exists. The first user in an organization is created via `backend/scripts/seed_dev_user.py`, run directly against the database -- not exposed as an API endpoint.

## File uploads (photos, ADR-0018)

- Uploaded photos are decoded and re-encoded via Pillow before being written to disk -- this both verifies the file is actually a real image (rejecting a spoofed `Content-Type`) and strips EXIF metadata (phone photos often embed GPS coordinates).
- Filenames are always server-generated (`uuid4`), never derived from the client-supplied filename -- eliminates path-traversal risk from a malicious filename.
- A content-type allowlist (`image/jpeg`, `image/png`, `image/webp`) and a size cap (`max_upload_size_bytes`, default 10 MB) are enforced before any file is written.
- **Known accepted risk:** uploaded photos are served unauthenticated at `/media/...` -- protected only by the URL containing an unguessable UUID filename, not real access control. Anyone who obtains a photo's exact URL can view it without logging in. Acceptable for a pre-public-facing internal tool (same class of tradeoff as the `localStorage` JWT storage decision, ADR-0007); revisit with real access control before this is customer-facing.
- **Known accepted risk:** local disk storage (not encrypted at rest, no redundancy, does not survive an ephemeral filesystem) -- see ADR-0018. Revisit once the backend is actually deployed somewhere with a real persistence story.

## Data handling

To be filled in once the data model exists (see [DATABASE.md](DATABASE.md)): what personal or sensitive data (if any) the system stores, how it's encrypted at rest/in transit, and retention/deletion policy.

## Database changes

No destructive migration (dropping columns/tables, irreversible data transforms) ships without: a reviewed migration script, a rollback path, and a backup verified beforehand. See [DATABASE.md](DATABASE.md).

## Reporting a vulnerability

This is currently a private, pre-release project with a single maintainer. Report suspected vulnerabilities directly to the maintainer rather than opening a public issue. This section will be expanded with a formal disclosure process before any public or multi-user release.

## Status

Pre-product. Authentication exists (see above); authorization (role/permission enforcement) and data-handling/encryption policy do not yet. This document will gain concrete sections as those systems are built — each addition should be a real decision recorded in [DECISIONS.md](DECISIONS.md), not boilerplate.
