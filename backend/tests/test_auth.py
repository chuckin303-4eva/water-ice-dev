from app.core.models.user import User


def test_login_success_returns_tokens(client, test_user: User) -> None:
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_is_rejected(client, test_user: User) -> None:
    response = client.post(
        "/auth/login", json={"email": test_user.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_email_is_rejected(client, test_user: User) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_requires_a_token(client, test_user: User) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_for_valid_token(client, test_user: User) -> None:
    login = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == test_user.email
    assert body["id"] == test_user.id


def test_refresh_issues_a_new_access_token(client, test_user: User) -> None:
    login = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    refresh_token = login.json()["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_rejects_an_access_token(client, test_user: User) -> None:
    login = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login.json()["access_token"]

    response = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_inactive_user_cannot_log_in(client, db_session, test_user: User) -> None:
    test_user.is_active = False
    db_session.add(test_user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 401


def test_register_creates_org_and_admin_user(client) -> None:
    response = client.post(
        "/auth/register",
        json={"organization_name": "New Co", "email": "founder@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "founder@example.com"
    assert me.json()["role"] == "admin"


def test_register_duplicate_email_is_rejected(client, test_user) -> None:
    response = client.post(
        "/auth/register",
        json={"organization_name": "New Co", "email": test_user.email, "password": "password123"},
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client) -> None:
    response = client.post(
        "/auth/register",
        json={"organization_name": "New Co", "email": "founder@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_malformed_email(client) -> None:
    response = client.post(
        "/auth/register",
        json={"organization_name": "New Co", "email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


def test_seed_style_user_with_no_role_defaults_to_member(client, test_user) -> None:
    """A user created outside this feature (e.g. backend/scripts/seed_dev_user.py)
    has no role row at all -- /auth/me should still work, treating them
    as a regular member rather than erroring.
    """
    login = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "correct-horse-battery-staple"},
    )
    access_token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "member"
