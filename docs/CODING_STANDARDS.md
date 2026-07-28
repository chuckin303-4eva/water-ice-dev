# Coding Standards

Language- and framework-specific rules will be appended here once the tech stack is chosen (see [ARCHITECTURE.md](ARCHITECTURE.md)). The rules below are stack-agnostic and apply from day one.

## Git workflow

Branches:
| Branch | Purpose | Branched from | Merges into |
|---|---|---|---|
| `main` | Production only. Always deployable. | — | — |
| `develop` | Integration branch for completed, tested work. | `main` | `main` (via release) |
| `feature/*` | New features. | `develop` | `develop` |
| `bugfix/*` | Non-urgent fixes. | `develop` | `develop` |
| `hotfix/*` | Urgent production fixes. | `main` | `main` and `develop` |

Naming: `feature/short-description`, `bugfix/short-description`, `hotfix/short-description` (kebab-case, no ticket-only names like `feature/123` — make it greppable).

## Before every commit

Run, in order, and do not commit if any fail:
1. **Tests** — full suite for touched areas at minimum.
2. **Linting** — project linter, zero new warnings introduced.
3. **Type checks** — project type checker (once a typed language/tooling is in place).
4. **Security checks** — dependency vulnerability scan and static analysis where configured.

A hook scaffold for this lives at `.githooks/pre-commit` (enable with `git config core.hooksPath .githooks`). It currently contains placeholders — each check gets wired in as the corresponding tool is adopted (see [ARCHITECTURE.md](ARCHITECTURE.md) for stack status).

## Commit messages

Every commit message must answer three questions:

```
<short summary line, imperative mood>

WHAT: what changed, concretely.
WHY: the problem or requirement that made this necessary.
IMPACT: what this affects — behavior, performance, security, API surface, migrations, etc. "None" is a valid answer but must be stated.
```

Example:
```
Add rate limiting to login endpoint

WHAT: Added a 5-requests-per-minute limit per IP on POST /auth/login.
WHY: Endpoint had no brute-force protection.
IMPACT: Legitimate users retrying rapidly will see 429s; no schema or API contract change.
```

## Pull requests

- One logical change per PR. Split unrelated changes.
- PR description restates WHAT/WHY/IMPACT from the commit(s).
- Update [CHANGELOG.md](CHANGELOG.md) for any user-facing or operationally meaningful change.
- Add or update a [DECISIONS.md](DECISIONS.md) entry if the PR makes an architectural decision, not just an implementation choice.
- No PR merges to `develop` or `main` with failing checks.

## Autonomous Execution Policy (ADR-0005)

Default mode is autonomous. Continue working until a logical milestone is complete; don't stop for routine implementation decisions or re-ask for approval once project direction is already established (which, on this project, most of it is — see the accepted ADRs). Implement the largest coherent unit of work reasonable before returning control. When multiple valid implementation choices exist, pick whichever best satisfies, in rough priority order: simplicity, maintainability, security, scalability, performance, low operating cost. Record significant architectural decisions in [DECISIONS.md](DECISIONS.md) as they're made, and keep going — don't wait for sign-off on the ADR itself.

**Pause and ask only when one of these occurs:**
1. A destructive database migration or irreversible data operation.
2. A change that would knowingly break backward compatibility.
3. Missing credentials, API keys, licenses, or required external resources.
4. A legal, compliance, or platform-policy limitation requiring a user decision.
5. Two or more fundamentally different business strategies are equally valid and the choice materially affects the product roadmap.

Otherwise, proceed. When a milestone completes, give a concise progress report — completed work, files created/modified, remaining work, recommended next milestone — then immediately continue to the next planned milestone unless interrupted or reprioritized. See ADR-0005 for the full rationale and what this replaced.

## Architecture conflict gate

Before implementing any requested work, check it against this standard, [ARCHITECTURE.md](ARCHITECTURE.md), and [DECISIONS.md](DECISIONS.md). If the work would introduce significant technical debt, duplicate existing functionality, or conflict with the established architecture (the core/module split, an accepted ADR, the stack in ADR-0002):

1. **Explain why** — name the specific debt, duplication, or conflicting decision.
2. **Recommend a better solution.**
3. **Record the conflict and the resolution** in [DECISIONS.md](DECISIONS.md).
4. **Proceed with the recommended alternative** — unless the situation also matches one of the Autonomous Execution Policy's five pause conditions above, in which case stop and wait as specified there.

This applies even when the request is direct and specific. Before ADR-0005 this gate paused for approval every time; it no longer does — explain and record, then act.

## General principles

- No new dependency without a one-line justification in the PR description (what it does, why the standard library or an existing dependency isn't enough).
- No secrets, API keys, tokens, or credentials committed, ever — use environment variables and `.env.example` (see [SECURITY.md](SECURITY.md)).
- No destructive schema change without a corresponding migration (see [DATABASE.md](DATABASE.md)).
- Prefer deleting code over commenting it out. Git history is the archive.
- Match existing patterns in the file/module you're editing before introducing a new one.
