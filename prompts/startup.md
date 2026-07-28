# Startup

Read this before taking any action in this repo. It's a checklist, not a
rulebook — the actual rules live in `/docs`; this just makes sure they get
read in the right order before anything happens.

1. **Orient.** Run `git status` and `git log --oneline -10`. Don't assume
   the state of the repo from memory of a previous session — check.
2. **Check current phase and priorities.** Read [docs/ROADMAP.md](../docs/ROADMAP.md).
   Don't work outside the current phase without flagging it (PM operating
   rules, same file).
3. **Check the latest decisions.** Skim [docs/DECISIONS.md](../docs/DECISIONS.md)
   for ADRs accepted since you last worked on this repo — architecture may
   have changed.
4. **Before starting a feature**, state business value, complexity,
   dependencies, risk, and expected user impact (PM operating rules,
   [docs/ROADMAP.md](../docs/ROADMAP.md)) — then proceed. This is
   transparency, not an approval gate.
5. **Before writing code**, run it through the architecture-conflict gate:
   [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md#architecture-conflict-gate).
   If it introduces significant tech debt, duplicates something that
   exists, or conflicts with an accepted ADR — explain, recommend a better
   solution, record it in [docs/DECISIONS.md](../docs/DECISIONS.md), and
   proceed with the recommendation.
6. **Operate autonomously per the [Autonomous Execution Policy](../docs/CODING_STANDARDS.md#autonomous-execution-policy-adr-0005)** —
   keep going through a full milestone without stopping for routine
   decisions. Only stop for: a destructive migration/irreversible data
   op, a backward-compatibility break, missing credentials/licenses/
   external resources, a legal/compliance/platform-policy limitation, or
   two genuinely equal strategic options that materially affect the
   roadmap. When a milestone completes, give the progress report
   (completed work, files touched, remaining work, recommended next
   milestone) and immediately continue unless interrupted.
7. **Route to the relevant prompt** for the kind of work:
   - Architecture/schema/design work → [architecture.md](architecture.md)
   - Writing or reviewing code → [coding.md](coding.md)
   - Cutting a release/deploying → [release.md](release.md)
   - Anything touching secrets, auth, or dependencies → [security.md](security.md)
