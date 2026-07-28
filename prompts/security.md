# Security

Authoritative source: [docs/SECURITY.md](../docs/SECURITY.md). This file
does not restate it — read it, don't rely on a summary of it.

Before touching anything involving secrets, auth, dependencies, or the
database:

1. Never commit a secret, API key, token, password, or credential —
   including in code, config, comments, commit messages, or test
   fixtures. If one is found already committed, treat it as compromised
   and say so — rotation is the fix, not a follow-up quiet edit.
2. New dependencies need a stated justification (see [coding.md](coding.md))
   and get checked against known vulnerabilities as tooling allows.
3. No destructive migration (dropped column/table, irreversible
   transform) without a reviewed rollback path and a verified backup —
   see [docs/DATABASE.md](../docs/DATABASE.md).
4. Anything that looks like a new attack surface (new endpoint accepting
   user input, new auth flow, new external integration) gets a security
   consideration called out explicitly when the work is proposed, not
   left implicit.

This project has no production deployment yet, so `docs/SECURITY.md`'s
vulnerability-reporting section is intentionally minimal — don't treat
that as license to skip the rest.
