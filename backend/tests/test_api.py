import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login(client):
    await client.post(
        "/api/auth/register",
        json={"email": "test@example.com"},
    )
    
    response = await client.post(
        "/api/auth/login",
        json={"email": "test@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
