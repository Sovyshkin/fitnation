import asyncio
from unittest.mock import Mock
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient, Response

from app.api.dependencies import get_event_service
from app.main import app
from app.services.delivery_store import EventDeliveryStore


API_KEY = "test-api-key-long-enough"
def post(path: str, *, json: dict, headers: dict[str, str]) -> Response:
    async def request() -> Response:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(path, json=json, headers=headers)

    return asyncio.run(request())


def payload(event: str = "WELCOME_DAY1") -> dict:
    return {
        "event": event,
        "recipient": {"email": "client@example.com", "name": "Анна"},
        "data": {},
    }


def test_invalid_api_key_returns_401() -> None:
    response = post("/api/v1/events", json=payload(), headers={"X-API-Key": "wrong"})
    assert response.status_code == 401
    assert response.json() == {
        "status": "error",
        "code": "unauthorized",
        "message": "Invalid API key",
    }


def test_unknown_event_returns_400() -> None:
    response = post(
        "/api/v1/events",
        json=payload("NOT_A_REAL_EVENT"),
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "unknown_event"


def test_invalid_email_returns_422() -> None:
    body = payload()
    body["recipient"]["email"] = "not-an-email"
    response = post("/api/v1/events", json=body, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    assert "input" not in response.text


def test_unsafe_url_returns_422() -> None:
    body = payload()
    body["data"]["support_url"] = "javascript:alert(1)"
    response = post("/api/v1/events", json=body, headers={"X-API-Key": API_KEY})
    assert response.status_code == 422
    assert "javascript" not in response.text


def test_missing_event_data_returns_400_without_smtp() -> None:
    response = post(
        "/api/v1/events",
        json=payload("SUBSCRIPTION_4DAYS_BEFORE"),
        headers={"X-API-Key": API_KEY},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_event_data"


def test_valid_event_calls_event_service() -> None:
    service = Mock()
    app.dependency_overrides[get_event_service] = lambda: service
    try:
        response = post("/api/v1/events", json=payload(), headers={"X-API-Key": API_KEY})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "status": "sent",
        "event": "WELCOME_DAY1",
        "recipient": "client@example.com",
    }
    service.process.assert_called_once()


def test_duplicate_event_id_does_not_send_twice(tmp_path) -> None:
    service = Mock()
    body = payload()
    body["event_id"] = "1c:welcome:membership-42:2026-09-22"
    deliveries = EventDeliveryStore(tmp_path / "deliveries.sqlite3", processing_ttl_seconds=60)
    app.dependency_overrides[get_event_service] = lambda: service
    try:
        with patch("app.api.events.get_event_delivery_store", return_value=deliveries):
            first = post("/api/v1/events", json=body, headers={"X-API-Key": API_KEY})
            second = post("/api/v1/events", json=body, headers={"X-API-Key": API_KEY})
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["status"] == "sent"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    service.process.assert_called_once()
