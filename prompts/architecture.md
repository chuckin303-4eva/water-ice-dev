# Architecture

Authoritative source: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) and
[docs/DECISIONS.md](../docs/DECISIONS.md). This file does not restate their
content — read them, don't rely on a summary of them.

Before proposing or changing anything architectural:

1. Read the current state of both files above — architecture evolves via
   accepted ADRs, so what's true today may not match an older memory of it.
2. Check whether the change conflicts with an accepted ADR (e.g. the
   core/industry-module split, no-PostGIS-for-v1, cross-tenant resource
   pooling, the ADR-0002 stack). If it does, that's the architecture-
   conflict gate in [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md#architecture-conflict-gate) —
   explain, recommend a better solution, record it, and proceed.
3. For a genuinely new architectural decision: state the business
   value/complexity/dependencies/risk/impact (PM operating rules in
   [docs/ROADMAP.md](../docs/ROADMAP.md)), then proceed — per the
   [Autonomous Execution Policy](../docs/CODING_STANDARDS.md#autonomous-execution-policy-adr-0005),
   this doesn't wait for approval unless it hits one of that policy's
   five pause conditions (destructive migration, backward-compat break,
   missing credentials/resources, legal/compliance limit, or a genuine
   fork between equally-valid business strategies).
4. Record it as a new ADR in docs/DECISIONS.md and update
   docs/ARCHITECTURE.md/docs/DATABASE.md as needed — don't let the docs
   fall behind the decision.
