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
4. **Before implementing anything non-trivial**, give the standing status
   report (current status, last milestone, blockers, recommended next
   task, files that will change, risks) and wait for approval — see
   [docs/ROADMAP.md](../docs/ROADMAP.md) PM operating rules.
5. **Before writing code**, run it through the architecture-conflict gate:
   [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md#architecture-conflict-gate).
   If it introduces significant tech debt, duplicates something that
   exists, or conflicts with an accepted ADR — stop, explain, recommend,
   wait.
6. **Route to the relevant prompt** for the kind of work:
   - Architecture/schema/design work → [architecture.md](architecture.md)
   - Writing or reviewing code → [coding.md](coding.md)
   - Cutting a release/deploying → [release.md](release.md)
   - Anything touching secrets, auth, or dependencies → [security.md](security.md)
