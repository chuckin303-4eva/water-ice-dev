"""Structural smoke test: the ORM metadata is well-formed and every Phase 1
table can be created. Runs against in-memory SQLite so it needs no external
database -- it is not a substitute for running the real Alembic migration
against Postgres, which uses Postgres-specific behavior these models don't
exercise (see docs/DATABASE.md and the migration in migrations/versions/).
"""

from sqlalchemy import create_engine, inspect

from app.core.models.base import Base

# Import triggers model registration on Base.metadata.
import app.core.models  # noqa: F401


def test_all_phase1_tables_are_created() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    table_names = set(inspect(engine).get_table_names())
    expected = {
        "organizations",
        "users",
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
        "states",
        "counties",
        "cities",
        "brands",
        "host_businesses",
        "locations",
        "location_call_notes",
        "update_log",
        "competitors",
    }
    assert expected.issubset(table_names)
