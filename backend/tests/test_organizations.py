from app.core.models.user import User


def _register(client, org_name: str, email: str, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"organization_name": org_name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_list_users_shows_org_roster(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")

    listing = client.get("/organizations/users", headers=admin_headers)
    assert listing.status_code == 200
    body = listing.json()
    assert len(body) == 1
    assert body[0]["email"] == "admin@acme.com"
    assert body[0]["role"] == "admin"


def test_admin_can_create_a_user(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")

    response = client.post(
        "/organizations/users",
        json={"email": "teammate@acme.com", "password": "password123", "role": "member"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "teammate@acme.com"
    assert body["role"] == "member"
    assert body["is_active"] is True

    listing = client.get("/organizations/users", headers=admin_headers).json()
    assert len(listing) == 2


def test_non_admin_cannot_create_a_user(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    client.post(
        "/organizations/users",
        json={"email": "teammate@acme.com", "password": "password123", "role": "member"},
        headers=admin_headers,
    )
    member_login = client.post(
        "/auth/login", json={"email": "teammate@acme.com", "password": "password123"}
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    response = client.post(
        "/organizations/users",
        json={"email": "another@acme.com", "password": "password123", "role": "member"},
        headers=member_headers,
    )
    assert response.status_code == 403


def test_create_user_duplicate_email_is_rejected(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")

    response = client.post(
        "/organizations/users",
        json={"email": "admin@acme.com", "password": "password123", "role": "member"},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_admin_can_update_a_teammates_role_and_active_status(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    create = client.post(
        "/organizations/users",
        json={"email": "teammate@acme.com", "password": "password123", "role": "member"},
        headers=admin_headers,
    )
    user_id = create.json()["id"]

    promote = client.put(
        f"/organizations/users/{user_id}", json={"role": "admin"}, headers=admin_headers
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "admin"

    deactivate = client.put(
        f"/organizations/users/{user_id}", json={"is_active": False}, headers=admin_headers
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False


def test_admin_cannot_modify_their_own_account(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    me = client.get("/auth/me", headers=admin_headers).json()

    response = client.put(
        f"/organizations/users/{me['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert response.status_code == 400


def test_admin_can_demote_a_second_admin_back_to_member(client) -> None:
    """No "last admin" business-rule guard exists (see
    organization_service.py's docstring for why one isn't needed) -- the
    real safety property is that self-modification is always blocked,
    which alone guarantees an org never reaches 0 admins. This confirms
    the ordinary demote-a-colleague path still works correctly.
    """
    admin_headers = _register(client, "Acme", "admin@acme.com")
    create = client.post(
        "/organizations/users",
        json={"email": "teammate@acme.com", "password": "password123", "role": "admin"},
        headers=admin_headers,
    )
    second_admin_id = create.json()["id"]

    demote = client.put(
        f"/organizations/users/{second_admin_id}", json={"role": "member"}, headers=admin_headers
    )
    assert demote.status_code == 200
    assert demote.json()["role"] == "member"


def test_demoted_admin_immediately_loses_admin_access(client) -> None:
    """Role changes take effect live -- the very next request from a
    just-demoted user is authorized against their new role, not a
    cached one.
    """
    admin_headers = _register(client, "Acme", "admin@acme.com")
    create = client.post(
        "/organizations/users",
        json={"email": "teammate@acme.com", "password": "password123", "role": "admin"},
        headers=admin_headers,
    )
    teammate_id = create.json()["id"]
    login = client.post("/auth/login", json={"email": "teammate@acme.com", "password": "password123"})
    teammate_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    client.put(f"/organizations/users/{teammate_id}", json={"role": "member"}, headers=admin_headers)

    response = client.post(
        "/organizations/users",
        json={"email": "another@acme.com", "password": "password123", "role": "member"},
        headers=teammate_headers,
    )
    assert response.status_code == 403


def test_users_are_scoped_to_their_own_organization(client) -> None:
    acme_headers = _register(client, "Acme", "admin@acme.com")
    widgets_headers = _register(client, "Widgets Inc", "admin@widgets.com")

    acme_users = client.get("/organizations/users", headers=acme_headers).json()
    widgets_users = client.get("/organizations/users", headers=widgets_headers).json()
    assert {u["email"] for u in acme_users} == {"admin@acme.com"}
    assert {u["email"] for u in widgets_users} == {"admin@widgets.com"}

    widgets_admin_id = widgets_users[0]["id"]
    cross_org_update = client.put(
        f"/organizations/users/{widgets_admin_id}", json={"is_active": False}, headers=acme_headers
    )
    assert cross_org_update.status_code == 404


def test_seed_style_user_defaults_to_member_role(client, test_user: User) -> None:
    from tests.conftest import auth_headers

    headers = auth_headers(client, test_user)
    listing = client.get("/organizations/users", headers=headers).json()
    assert listing[0]["role"] == "member"
