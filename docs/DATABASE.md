# Database

**Status: Pending.** No database or data model exists yet. This document will describe the schema, relationships, and migration policy once one is chosen (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Migration policy (in force now, regardless of stack)

- Every schema change ships as a versioned migration file, never a manual/ad-hoc change against any environment.
- No destructive migration (dropped column/table, irreversible transform, type narrowing that loses data) merges without: a reviewed rollback path and a verified backup immediately before it runs in production.
- Migrations run in the same order in every environment (local, staging, production) — no environment-specific schema drift.
- Every migration is reviewed for lock behavior on the target database before it runs against production-scale data.

## Schema

_To be documented per-entity once the data model exists: table/collection name, fields, types, relationships, indexes, and the reason each index exists._

## Entity-relationship overview

_Diagram or description once entities exist._
