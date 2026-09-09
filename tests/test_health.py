import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


def get(path: str) -> Response:
    async def request() -> Response:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(request())


def test_health() -> None:
    response = get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root() -> None:
    response = get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "FITNATION Notification Service"
