def _register(client, org_name: str, email: str, password: str = "password123") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"organization_name": org_name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _add_member(client, admin_headers, email: str, password: str = "password123") -> dict[str, str]:
    create = client.post(
        "/organizations/users",
        json={"email": email, "password": password, "role": "member"},
        headers=admin_headers,
    )
    assert create.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_new_org_defaults_to_free_plan(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.get("/billing/subscription", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["slug"] == "free"
    assert body["status"] == "active"
    assert body["provider"] == "none"
    assert body["current_period_start"] is None


def test_list_plans_returns_catalog(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.get("/billing/plans", headers=admin_headers)
    assert response.status_code == 200
    slugs = {p["slug"] for p in response.json()}
    assert slugs == {"free", "starter", "pro"}


def test_subscribe_to_paid_plan(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.post("/billing/subscribe", json={"plan_slug": "starter"}, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["slug"] == "starter"
    assert body["status"] == "active"
    assert body["provider"] == "mock"
    assert body["current_period_start"] is not None
    assert body["current_period_end"] is not None


def test_subscribe_creates_invoice(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    client.post("/billing/subscribe", json={"plan_slug": "starter"}, headers=admin_headers)

    response = client.get("/billing/invoices", headers=admin_headers)
    assert response.status_code == 200
    invoices = response.json()
    assert len(invoices) == 1
    assert invoices[0]["plan_slug"] == "starter"
    assert invoices[0]["amount_cents"] == 4900
    assert invoices[0]["status"] == "paid"


def test_switching_plans_updates_subscription_and_adds_invoice(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    client.post("/billing/subscribe", json={"plan_slug": "starter"}, headers=admin_headers)
    response = client.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=admin_headers)
    assert response.json()["plan"]["slug"] == "pro"

    invoices = client.get("/billing/invoices", headers=admin_headers).json()
    assert len(invoices) == 2
    assert {inv["plan_slug"] for inv in invoices} == {"starter", "pro"}


def test_cancel_reverts_to_free(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    client.post("/billing/subscribe", json={"plan_slug": "pro"}, headers=admin_headers)

    response = client.post("/billing/cancel", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["slug"] == "free"
    assert body["provider"] == "none"

    # Cancellation doesn't erase billing history.
    invoices = client.get("/billing/invoices", headers=admin_headers).json()
    assert len(invoices) == 1


def test_cancel_without_active_subscription_is_rejected(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.post("/billing/cancel", headers=admin_headers)
    assert response.status_code == 409


def test_cannot_subscribe_to_free_plan_directly(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.post("/billing/subscribe", json={"plan_slug": "free"}, headers=admin_headers)
    assert response.status_code == 422


def test_subscribe_to_unknown_plan_is_rejected(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    response = client.post("/billing/subscribe", json={"plan_slug": "enterprise"}, headers=admin_headers)
    assert response.status_code == 422


def test_member_can_view_but_not_manage_billing(client) -> None:
    admin_headers = _register(client, "Acme", "admin@acme.com")
    member_headers = _add_member(client, admin_headers, "member@acme.com")

    assert client.get("/billing/plans", headers=member_headers).status_code == 200
    assert client.get("/billing/subscription", headers=member_headers).status_code == 200
    assert (
        client.post("/billing/subscribe", json={"plan_slug": "starter"}, headers=member_headers).status_code
        == 403
    )
    assert client.post("/billing/cancel", headers=member_headers).status_code == 403
    assert client.get("/billing/invoices", headers=member_headers).status_code == 403
