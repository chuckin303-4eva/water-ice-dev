# water-ice-dev

## Purpose

**Status: pending.** Product scope has not been defined yet. This README and the linked docs will be filled in as the project takes shape — see [docs/ROADMAP.md](docs/ROADMAP.md) for current status and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design once it exists.

## Installation

_TBD — depends on the tech stack chosen in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)._

## Development environment

_TBD._ Once tooling is chosen:
1. Clone the repo and check out `develop`.
2. Copy `.env.example` to `.env` and fill in local values (never commit `.env` — see [docs/SECURITY.md](docs/SECURITY.md)).
3. Install dependencies and run the local dev setup (documented here once it exists).
4. Enable local git hooks: `git config core.hooksPath .githooks`.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) (pending — no hosting platform chosen yet).

## Contribution process

This repo uses a four-branch git workflow — see [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md#git-workflow) for full detail:

- `main` — production only.
- `develop` — integration branch.
- `feature/*`, `bugfix/*` — branch from `develop`, merge back into `develop`.
- `hotfix/*` — branch from `main`, merge into both `main` and `develop`.

Before every commit: tests, linting, type checks, and security checks must pass (see [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md)). Commit messages must state WHAT changed, WHY, and the IMPACT. Update [docs/CHANGELOG.md](docs/CHANGELOG.md) for meaningful changes, and [docs/DECISIONS.md](docs/DECISIONS.md) whenever an architectural decision is made.

## Documentation index

| Doc | Purpose |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, tech stack, components |
| [DATABASE.md](docs/DATABASE.md) | Schema, relationships, migration policy |
| [API.md](docs/API.md) | Endpoints, auth, conventions |
| [ROADMAP.md](docs/ROADMAP.md) | What's planned, now/next/later |
| [CHANGELOG.md](docs/CHANGELOG.md) | Notable changes per release |
| [DECISIONS.md](docs/DECISIONS.md) | Architecture decision records |
| [SECURITY.md](docs/SECURITY.md) | Secrets handling, vulnerability reporting |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Environments, release, rollback |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | How to use the product |
| [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Git workflow, commit format, PR process |
