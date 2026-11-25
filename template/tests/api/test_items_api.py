from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import MakeAuthHeaders


def test_create_then_get_item(client: TestClient, make_auth_headers: MakeAuthHeaders) -> None:
    headers = make_auth_headers()
    created = client.post("/v1/items", json={"name": "book"}, headers=headers)

    assert created.status_code == 201
    body = created.json()
    fetched = client.get(f"/v1/items/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_validates_payload(client: TestClient, make_auth_headers: MakeAuthHeaders) -> None:
    response = client.post("/v1/items", json={"name": ""}, headers=make_auth_headers())

    assert response.status_code == 422
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json()["errors"][0]["loc"] == ["body", "name"]


def test_create_rejects_client_supplied_owner(
    client: TestClient, make_auth_headers: MakeAuthHeaders
) -> None:
    response = client.post(
        "/v1/items", json={"name": "book", "owner_id": "mallory"}, headers=make_auth_headers()
    )

    assert response.status_code == 422


def test_domain_errors_map_to_422(client: TestClient, make_auth_headers: MakeAuthHeaders) -> None:
    response = client.post("/v1/items", json={"name": "   "}, headers=make_auth_headers())

    assert response.status_code == 422
    assert "blank" in response.json()["detail"]


def test_unknown_item_returns_404(client: TestClient, make_auth_headers: MakeAuthHeaders) -> None:
    response = client.get(f"/v1/items/{uuid4()}", headers=make_auth_headers())

    assert response.status_code == 404
    assert response.json()["status"] == 404


def test_responses_carry_correlation_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "a" * 32})

    assert response.headers["X-Request-ID"] == "a" * 32
