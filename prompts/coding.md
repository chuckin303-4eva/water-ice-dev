# Coding

Authoritative source: [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md).
This file does not restate it — read it, don't rely on a summary of it.

Before writing code:

1. Run the [architecture-conflict gate](../docs/CODING_STANDARDS.md#architecture-conflict-gate) —
   stop, explain, recommend, wait if the work conflicts with existing
   architecture or duplicates something that exists.
2. Confirm the branch matches the workflow (`feature/*`, `bugfix/*`,
   `hotfix/*` off the right base — see the git workflow table).
3. Justify any new dependency in one line (what it does, why nothing
   existing covers it) before adding it.

Before every commit:

1. Run tests, linting, type checks, and security checks — the
   `.githooks/pre-commit` hook enforces what's wired in; don't bypass it.
2. Write the commit message in WHAT/WHY/IMPACT form.
3. Update [docs/CHANGELOG.md](../docs/CHANGELOG.md) if the change is
   user-facing or operationally meaningful.
4. Update [docs/DECISIONS.md](../docs/DECISIONS.md) if the change makes an
   architectural decision, not just an implementation choice.
