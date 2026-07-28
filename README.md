# water-ice-dev

## Purpose

**Ice & Water Intelligence** — a location-intelligence SaaS for ice and water vending operators (competitors, market opportunities, expansion sites, host businesses). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design and [docs/ROADMAP.md](docs/ROADMAP.md) for current build phase. The product is early: Phase 1 (MVP) is in progress and the frontend doesn't exist yet.

## Installation

Requires Python 3.12 and Docker Desktop (for Postgres).

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # PowerShell. cmd.exe: venv\Scripts\activate.bat -- macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
```

If PowerShell blocks the activation script (`running scripts is disabled on this system`), either run `Set-ExecutionPolicy -Scope Process RemoteSigned` first, or skip activation entirely and call the venv's executables directly, e.g. `.\venv\Scripts\alembic.exe upgrade head`, `.\venv\Scripts\pytest.exe`.

## Development environment

1. Clone the repo and check out `develop`.
2. Copy `.env.example` to `.env` at the repo root and fill in local values (never commit `.env` — see [docs/SECURITY.md](docs/SECURITY.md)).
3. Make sure Docker Desktop is actually running (not just installed) — check the system tray for the whale icon. Then start Postgres: `docker compose -f infra/docker-compose.yml --env-file .env up -d`
4. From `backend/`, with the virtualenv active, run the migration: `alembic upgrade head`
5. Run the API: `uvicorn app.main:app --reload` — then check `http://localhost:8000/health`
6. Run tests: `pytest`
7. Enable local git hooks: `git config core.hooksPath .githooks`

The frontend (React/Vite) doesn't exist yet — see [docs/ROADMAP.md](docs/ROADMAP.md) Phase 1.

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
