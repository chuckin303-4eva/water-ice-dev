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

## Data handling

To be filled in once the data model exists (see [DATABASE.md](DATABASE.md)): what personal or sensitive data (if any) the system stores, how it's encrypted at rest/in transit, and retention/deletion policy.

## Database changes

No destructive migration (dropping columns/tables, irreversible data transforms) ships without: a reviewed migration script, a rollback path, and a backup verified beforehand. See [DATABASE.md](DATABASE.md).

## Reporting a vulnerability

This is currently a private, pre-release project with a single maintainer. Report suspected vulnerabilities directly to the maintainer rather than opening a public issue. This section will be expanded with a formal disclosure process before any public or multi-user release.

## Status

Pre-product. No authentication, authorization, or data-handling systems exist yet. This document will gain concrete sections (threat model, auth model, encryption approach) as those systems are built — each addition should be a real decision recorded in [DECISIONS.md](DECISIONS.md), not boilerplate.
