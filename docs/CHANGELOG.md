# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/): group entries under Added / Changed / Fixed / Removed / Security, newest release at top.

## [Unreleased]

### Added
- Repository governance structure: `/docs` (ARCHITECTURE, DATABASE, API, ROADMAP, DECISIONS, SECURITY, DEPLOYMENT, USER_GUIDE, CODING_STANDARDS), root README, git branching model (`main`/`develop`/`feature`/`bugfix`/`hotfix`), commit message template, and pre-commit hook scaffold.
- Product direction defined: "Ice & Water Intelligence" location-intelligence SaaS. Stack, core/module architecture, and schema documented in ARCHITECTURE.md and DATABASE.md; recorded in DECISIONS.md as ADR-0002 (Accepted): no PostGIS for v1 (plain lat/lng), cross-tenant resource-pooling confirmed as a core feature, monorepo confirmed.
- Full schema defined (ADR-0003, Accepted): geography (states/counties/cities), locations (full required field set, UUID PK), brands, host_businesses, competitors (site-level), opportunities, photos/documents/reviews (polymorphic attachments), validation_queue, update_log (append-only audit trail), tasks, settings.
- Market Refresh Engine designed (ADR-0004, Accepted): replaceable-provider architecture (OpenStreetMap/Overpass, US Census for v1; USGS/NOAA registered but unbuilt; paid rating/review/photo source deferred until budget exists), refresh -> validation_queue -> human approval -> locations update -> update_log workflow, in-process async execution with no new infrastructure. New refresh_runs table.
