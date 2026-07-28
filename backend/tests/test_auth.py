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
