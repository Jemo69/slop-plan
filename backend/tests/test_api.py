import tempfile
import os
import pytest
import pytest_asyncio
from tortoise import Tortoise

TEST_DB = tempfile.mktemp(suffix=".db")

TEST_TORTOISE = {
    "connections": {"default": {"engine": "tortoise.backends.sqlite", "credentials": {"file_path": TEST_DB}}},
    "apps": {"models": {"models": ["db"], "default_connection": "default"}},
}

@pytest_asyncio.fixture(autouse=True)
async def init_db():
    import main
    main._db_initialized = True
    await Tortoise.init(config=TEST_TORTOISE)
    await Tortoise.generate_schemas()
    yield
    main._db_initialized = False
    await Tortoise.close_connections()
    try:
        os.remove(TEST_DB)
    except FileNotFoundError:
        pass

@pytest.mark.asyncio
async def test_dashboard_has_home_button():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/dashboard")
        assert r.status_code == 200
        assert "Home" in r.text
        assert "/dashboard" in r.text

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
        r = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "secret123",
        })
        assert r.status_code == 201
        data = r.json()
        assert "api_key" in data
        assert data["has_password"] is True

        r2 = await client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "secret123",
        })
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
        assert "Dashboard" in rp_pub.text

@pytest.mark.asyncio
async def test_register_requires_password():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/auth/register", json={"email": "test@example.com"})
        assert r.status_code == 422

@pytest.mark.asyncio
async def test_register_rejects_short_password():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "ab",
        })
        assert r.status_code == 422

@pytest.mark.asyncio
async def test_login_wrong_password():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "secret123",
        })
        r = await client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert r.status_code == 401
        assert "Invalid password" in r.json()["detail"]

@pytest.mark.asyncio
async def test_login_missing_password():
    from httpx import AsyncClient, ASGITransport
    from main import app
    from services import hash_password
    from db import User
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await User.create(
            email="nopass@example.com",
            api_key="plan_testnopass",
            password_hash=None,
        )
        r = await client.post("/api/auth/login", json={
            "email": "nopass@example.com",
            "password": "whatever",
        })
        assert r.status_code == 400
        assert "no password" in r.json()["detail"].lower()


async def _register_and_get_headers(client, email, password="secret123"):
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    api_key = r.json()["api_key"]
    return {"Authorization": f"Bearer {api_key}"}


@pytest.mark.asyncio
async def test_pin_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "pin1@example.com")

        rp = await client.post("/api/projects", json={"name": "Proj"}, headers=headers)
        assert rp.status_code == 201
        pid = rp.json()["id"]
        assert rp.json()["is_pinned"] is False

        rpin = await client.post(f"/api/projects/{pid}/pin", headers=headers)
        assert rpin.status_code == 201
        assert rpin.json()["is_pinned"] is True

        rl = await client.get("/api/projects", headers=headers)
        assert rl.json()["projects"][0]["is_pinned"] is True


@pytest.mark.asyncio
async def test_unpin_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "unpin1@example.com")

        rp = await client.post("/api/projects", json={"name": "Proj"}, headers=headers)
        pid = rp.json()["id"]

        await client.post(f"/api/projects/{pid}/pin", headers=headers)

        runpin = await client.delete(f"/api/projects/{pid}/pin", headers=headers)
        assert runpin.status_code == 204

        rl = await client.get("/api/projects", headers=headers)
        assert rl.json()["projects"][0]["is_pinned"] is False


@pytest.mark.asyncio
async def test_pin_is_idempotent():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "idem1@example.com")

        rp = await client.post("/api/projects", json={"name": "Proj"}, headers=headers)
        pid = rp.json()["id"]

        r1 = await client.post(f"/api/projects/{pid}/pin", headers=headers)
        assert r1.status_code == 201
        r2 = await client.post(f"/api/projects/{pid}/pin", headers=headers)
        assert r2.status_code == 201
        assert r2.json()["is_pinned"] is True


@pytest.mark.asyncio
async def test_project_pinning_is_per_user():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h1 = await _register_and_get_headers(client, "user_a@example.com")
        h2 = await _register_and_get_headers(client, "user_b@example.com")

        rp1 = await client.post("/api/projects", json={"name": "ForA"}, headers=h1)
        pid1 = rp1.json()["id"]

        rp2 = await client.post("/api/projects", json={"name": "ForB"}, headers=h2)
        pid2 = rp2.json()["id"]

        await client.post(f"/api/projects/{pid1}/pin", headers=h1)

        rl1 = await client.get("/api/projects", headers=h1)
        assert rl1.json()["projects"][0]["is_pinned"] is True
        assert rl1.json()["projects"][0]["name"] == "ForA"

        rl2 = await client.get("/api/projects", headers=h2)
        proj_b = [p for p in rl2.json()["projects"] if p["id"] == pid2]
        assert len(proj_b) == 1
        assert proj_b[0]["is_pinned"] is False


@pytest.mark.asyncio
async def test_pinned_projects_sort_first():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "sort1@example.com")

        rp1 = await client.post("/api/projects", json={"name": "Alpha"}, headers=headers)
        rp2 = await client.post("/api/projects", json={"name": "Beta"}, headers=headers)
        pid2 = rp2.json()["id"]

        await client.post(f"/api/projects/{pid2}/pin", headers=headers)

        rl = await client.get("/api/projects", headers=headers)
        projects = rl.json()["projects"]
        assert projects[0]["name"] == "Beta"
        assert projects[0]["is_pinned"] is True
        assert projects[1]["name"] == "Alpha"
        assert projects[1]["is_pinned"] is False


@pytest.mark.asyncio
async def test_pin_nonexistent_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "pinbad@example.com")
        r = await client.post(
            "/api/projects/00000000-0000-0000-0000-000000000000/pin",
            headers=headers,
        )
        assert r.status_code == 404
