import tempfile
import os
import pytest
import pytest_asyncio
from tortoise import Tortoise

TEST_DB = tempfile.mktemp(suffix=".db")

TEST_TORTOISE = {
    "connections": {"default": {"engine": "tortoise.backends.sqlite", "credentials": {"file_path": TEST_DB}}},
    "apps": {"models": {"models": ["models"], "default_connection": "default"}},
}

@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await Tortoise.init(config=TEST_TORTOISE)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
    try:
        os.remove(TEST_DB)
    except FileNotFoundError:
        pass

@pytest.mark.asyncio
async def test_root():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/")
        assert r.status_code == 200

@pytest.mark.asyncio
async def test_register_flow():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/auth/register", json={"email": "test@example.com"})
        assert r.status_code == 201
        assert "api_key" in r.json()

        r2 = await client.post("/api/auth/login", json={"email": "test@example.com"})
        assert r2.status_code == 200
        api_key = r2.json()["api_key"]
        headers = {"Authorization": f"Bearer {api_key}"}

        rp = await client.post("/api/projects", json={"name": "My Project"}, headers=headers)
        assert rp.status_code == 201
        project_id = rp.json()["id"]

        rl = await client.get("/api/projects", headers=headers)
        assert rl.status_code == 200
        assert len(rl.json()["projects"]) == 1

        rc = await client.post(
            "/api/plans",
            json={
                "project_id": project_id,
                "title": "Test Plan",
                "html_content": "<html><head></head><body>hello</body></html>",
                "is_public": True,
            },
            headers=headers,
        )
        assert rc.status_code == 201
        plan = rc.json()
        assert plan["title"] == "Test Plan"

        rg = await client.get(f"/api/plans/{plan['id']}", headers=headers)
        assert rg.status_code == 200

        rp_pub = await client.get(f"/p/{plan['slug']}")
        assert rp_pub.status_code == 200
        assert "hello" in rp_pub.text
