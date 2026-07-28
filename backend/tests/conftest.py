"""Shared test fixtures. Auth/route tests run against an in-memory SQLite
database (same approach as test_models.py) rather than the real Postgres
instance -- fast, self-contained, sufficient for exercising application
logic. It does not substitute for running the real migration against
Postgres (see README.md / prompts/coding.md).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.core.models  # noqa: F401 -- registers models on Base.metadata
from app.core.models.base import Base
from app.core.models.organization import Organization
from app.core.models.user import User
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db_session: Session) -> User:
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.flush()

    user = User(
        organization_id=org.id,
        email="test@example.com",
        hashed_password=hash_password("correct-horse-battery-staple"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
