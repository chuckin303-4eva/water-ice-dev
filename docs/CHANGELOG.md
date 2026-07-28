# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): group entries under Added / Changed / Fixed / Removed / Security, newest release at top.

## [Unreleased]

### Added
- Repository governance structure: `/docs` (ARCHITECTURE, DATABASE, API, ROADMAP, DECISIONS, SECURITY, DEPLOYMENT, USER_GUIDE, CODING_STANDARDS), root README, git branching model (`main`/`develop`/`feature`/`bugfix`/`hotfix`), commit message template, and pre-commit hook scaffold.
- Product direction defined: "Ice & Water Intelligence" location-intelligence SaaS. Stack, core/module architecture, and schema documented in ARCHITECTURE.md and DATABASE.md; recorded in DECISIONS.md as ADR-0002 (Accepted): no PostGIS for v1 (plain lat/lng), cross-tenant resource-pooling confirmed as a core feature, monorepo confirmed.
- Full schema defined (ADR-0003, Accepted): geography (states/counties/cities), locations (full required field set, UUID PK), brands, host_businesses, competitors (site-level), opportunities, photos/documents/reviews (polymorphic attachments), validation_queue, update_log (append-only audit trail), tasks, settings.
- Market Refresh Engine designed (ADR-0004, Accepted): replaceable-provider architecture (OpenStreetMap/Overpass, US Census for v1; USGS/NOAA registered but unbuilt; paid rating/review/photo source deferred until budget exists), refresh -> validation_queue -> human approval -> locations update -> update_log workflow, in-process async execution with no new infrastructure. New refresh_runs table.
- ROADMAP.md restructured into four gated phases (MVP, Validation & Enrichment, Automation & Monetization, Advanced) with every feature ranked Critical/High/Medium/Low, per new PM operating rules.
- Backend project scaffolded (Phase 1, item 1): FastAPI app skeleton, SQLAlchemy models and initial Alembic migration for the Phase-1 subset of the schema (organizations, users, roles, permissions, role_permissions, user_roles, states, counties, cities, brands, host_businesses, locations), Postgres via `infra/docker-compose.yml`, `/health` endpoint, and a starter test suite (`pytest`). No API routes, auth, or business logic yet -- scoped strictly to project skeleton + database per ADR-0002/ADR-0003.
- Added an architecture-conflict gate to CODING_STANDARDS.md: work that would introduce significant tech debt, duplicate existing functionality, or conflict with an accepted ADR must stop, explain why, recommend a better solution, and wait for approval before implementation -- even when directly requested.
- Added `/prompts` (startup, architecture, coding, release, security): short, agent-facing checklists that point to the authoritative docs/ files rather than duplicating them, so there's one source of truth. `startup.md` is the entry point to read before taking any action.
