from uuid import uuid4

from fastapi.testclient import TestClient


def test_create_then_get_item(client: TestClient) -> None:
    created = client.post("/items", json={"name": "book"})

    assert created.status_code == 201
    body = created.json()
    fetched = client.get(f"/items/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_create_validates_payload(client: TestClient) -> None:
    response = client.post("/items", json={"name": ""})

    assert response.status_code == 422


def test_domain_errors_map_to_422(client: TestClient) -> None:
    response = client.post("/items", json={"name": "   "})

    assert response.status_code == 422
    assert "blank" in response.json()["detail"]


def test_unknown_item_returns_404(client: TestClient) -> None:
    response = client.get(f"/items/{uuid4()}")

    assert response.status_code == 404


def test_responses_carry_correlation_id(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "a" * 32})

    assert response.headers["X-Request-ID"] == "a" * 32
