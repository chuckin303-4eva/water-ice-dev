"""Create an organization + user for local login testing.

There is no self-serve registration or admin dashboard yet (Phase 1 item
8 in docs/ROADMAP.md), so this is the only way to get a first user into
the database. Usage:

    python scripts/seed_dev_user.py --org "Test Org" --email you@example.com --password changeme
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.models.organization import Organization  # noqa: E402
from app.core.models.user import User  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", required=True, help="Organization name")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing is not None:
            print(f"User {args.email} already exists (id={existing.id}); nothing to do.")
            return

        org = Organization(name=args.org)
        db.add(org)
        db.flush()  # assigns org.id without committing yet

        user = User(
            organization_id=org.id,
            email=args.email,
            hashed_password=hash_password(args.password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created organization '{org.name}' (id={org.id}) and user {user.email} (id={user.id}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
