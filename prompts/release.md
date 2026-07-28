# Release

Authoritative source: [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) and
[docs/CHANGELOG.md](../docs/CHANGELOG.md). This file does not restate
them — read them, don't rely on a summary of them.

**Current status:** no hosting platform is chosen yet and no release has
shipped — `docs/DEPLOYMENT.md` is still marked pending. There is no real
release process to follow yet. Don't invent one; when this becomes
relevant (Phase 3 per [docs/ROADMAP.md](../docs/ROADMAP.md)), propose the
environments/process/rollback plan as an architectural decision (see
[architecture.md](architecture.md)) and record it as an ADR before acting
on it.

Until then, the only "release" discipline that applies:

1. `docs/CHANGELOG.md` [Unreleased] section stays current with every
   meaningful change (this is already in force — see
   [coding.md](coding.md)).
2. `main` stays production-only and always deployable, even with no
   production to deploy to yet — see the git workflow in
   [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md#git-workflow).
