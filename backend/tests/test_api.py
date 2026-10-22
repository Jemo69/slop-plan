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
        assert "Dashboard" in r.text

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
        # Anonymous visitors must not see the dashboard nav bar.
        assert "Dashboard" not in rp_pub.text

        rp_signed_in = await client.get(f"/p/{plan['slug']}?token={api_key}")
        assert rp_signed_in.status_code == 200
        assert "Dashboard" in rp_signed_in.text

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


@pytest.mark.asyncio
async def test_archive_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "arch1@example.com")

        rp = await client.post("/api/projects", json={"name": "ToArchive"}, headers=headers)
        assert rp.status_code == 201
        pid = rp.json()["id"]
        assert rp.json()["is_archived"] is False

        rar = await client.post(f"/api/projects/{pid}/archive", headers=headers)
        assert rar.status_code == 200
        assert rar.json()["is_archived"] is True

        rl = await client.get("/api/projects", headers=headers)
        assert rl.status_code == 200
        assert len(rl.json()["projects"]) == 0


@pytest.mark.asyncio
async def test_unarchive_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "unarch1@example.com")

        rp = await client.post("/api/projects", json={"name": "ToUnarchive"}, headers=headers)
        pid = rp.json()["id"]

        await client.post(f"/api/projects/{pid}/archive", headers=headers)

        rlear = await client.post(f"/api/projects/{pid}/unarchive", headers=headers)
        assert rlear.status_code == 200
        assert rlear.json()["is_archived"] is False

        rl = await client.get("/api/projects", headers=headers)
        assert rl.status_code == 200
        assert len(rl.json()["projects"]) == 1
        assert rl.json()["projects"][0]["name"] == "ToUnarchive"


@pytest.mark.asyncio
async def test_archive_nonexistent_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "archbad@example.com")
        r = await client.post(
            "/api/projects/00000000-0000-0000-0000-000000000000/archive",
            headers=headers,
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_unarchive_nonexistent_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "unarchbad@example.com")
        r = await client.post(
            "/api/projects/00000000-0000-0000-0000-000000000000/unarchive",
            headers=headers,
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_cascades_plans():
    from httpx import AsyncClient, ASGITransport
    from main import app
    from db import Plan
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "del1@example.com")

        rp = await client.post("/api/projects", json={"name": "ToDelete"}, headers=headers)
        assert rp.status_code == 201
        pid = rp.json()["id"]

        rc = await client.post(
            "/api/plans",
            json={
                "project_id": pid,
                "title": "Plan A",
                "html_content": "<html></html>",
            },
            headers=headers,
        )
        assert rc.status_code == 201
        plan_id = rc.json()["id"]

        rd = await client.delete(f"/api/projects/{pid}", headers=headers)
        assert rd.status_code == 204

        lingering_plan = await Plan.filter(id=plan_id).first()
        assert lingering_plan is None

        rl = await client.get("/api/projects", headers=headers)
        assert len(rl.json()["projects"]) == 0


@pytest.mark.asyncio
async def test_delete_project_not_found():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "delbad@example.com")
        r = await client.delete(
            "/api/projects/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_isolated_per_user():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h1 = await _register_and_get_headers(client, "deluser_a@example.com")
        h2 = await _register_and_get_headers(client, "deluser_b@example.com")

        rp1 = await client.post("/api/projects", json={"name": "UserAProj"}, headers=h1)
        pid1 = rp1.json()["id"]

        rp2 = await client.post("/api/projects", json={"name": "UserBProj"}, headers=h2)
        pid2 = rp2.json()["id"]

        rd = await client.delete(f"/api/projects/{pid1}", headers=h1)
        assert rd.status_code == 204

        rl2 = await client.get("/api/projects", headers=h2)
        assert any(p["id"] == pid2 for p in rl2.json()["projects"])


@pytest.mark.asyncio
async def test_archive_page():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/archive")
        assert r.status_code == 200
        assert "Archive" in r.text
        assert "SLOP_PLANS_ARCHIVE__" in r.text


@pytest.mark.asyncio
async def test_api_returns_503_when_database_is_unavailable():
    """A dead database must fail fast, not hang until the function timeout."""
    import time

    import main
    from httpx import AsyncClient, ASGITransport
    from main import app

    main._db_state["unavailable"] = True
    main._db_state["reason"] = "test"
    # Skip the periodic recheck so the request observes the broken state.
    main._db_state["checked_at"] = time.monotonic()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/register", json={"email": "x@example.com", "password": "secret123"}
            )
            assert r.status_code == 503
            assert r.json()["detail"] == "database unavailable"

            # Static pages keep working while the database is down.
            home = await c.get("/")
            assert home.status_code == 200
    finally:
        main._db_state["unavailable"] = False
        main._db_state["reason"] = ""


@pytest.mark.asyncio
async def test_database_recheck_clears_the_unavailable_flag():
    """A recovered database must bring the API back without a redeploy."""
    import time

    import main
    from httpx import AsyncClient, ASGITransport
    from main import app

    main._db_state["unavailable"] = True
    main._db_state["reason"] = "test"
    # Age the last check so the middleware is allowed to re-probe.
    main._db_state["checked_at"] = time.monotonic() - 3600
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/auth/register", json={"email": "recover@example.com", "password": "secret123"}
            )
            assert r.status_code == 201
            assert main._db_state["unavailable"] is False
    finally:
        main._db_state["unavailable"] = False
        main._db_state["reason"] = ""


@pytest.mark.asyncio
async def test_archive_and_unarchive_plan():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "planarchive@example.com")
        project = await client.post("/api/projects", json={"name": "Plan archive"}, headers=headers)
        project_id = project.json()["id"]
        created = await client.post(
            "/api/plans",
            json={
                "project_id": project_id,
                "title": "Restorable plan",
                "html_content": "<p>restorable</p>",
                "is_public": True,
            },
            headers=headers,
        )
        plan = created.json()
        plan_id = plan["id"]

        archived = await client.post(f"/api/plans/{plan_id}/archive", headers=headers)
        assert archived.status_code == 200
        assert archived.json()["is_archived"] is True
        assert (await client.get(f"/p/{plan['slug']}")).status_code == 404

        restored = await client.post(f"/api/plans/{plan_id}/unarchive", headers=headers)
        assert restored.status_code == 200
        assert restored.json()["is_archived"] is False
        assert (await client.get(f"/p/{plan['slug']}")).status_code == 200


@pytest.mark.asyncio
async def test_plan_response_has_no_approval_fields():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "noapproval@example.com")
        rp = await client.post("/api/projects", json={"name": "NoApproval"}, headers=headers)
        pid = rp.json()["id"]
        rc = await client.post(
            "/api/plans",
            json={"project_id": pid, "title": "P", "html_content": "<p>hi</p>"},
            headers=headers,
        )
        assert rc.status_code == 201
        body = rc.json()
        assert "is_approved" not in body
        assert "approved_by" not in body
        assert "approved_at" not in body

        rl = await client.get("/api/plans", headers=headers)
        plan = rl.json()["plans"][0]
        assert "is_approved" not in plan


@pytest.mark.asyncio
async def test_archived_projects_visible_with_param():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "archview1@example.com")

        rp = await client.post("/api/projects", json={"name": "ActiveProj"}, headers=headers)
        rp2 = await client.post("/api/projects", json={"name": "ArchivedProj"}, headers=headers)
        pid2 = rp2.json()["id"]

        await client.post(f"/api/projects/{pid2}/archive", headers=headers)

        rl = await client.get("/api/projects", headers=headers)
        assert rl.status_code == 200
        assert all(not p["is_archived"] for p in rl.json()["projects"])

        rl_arch = await client.get("/api/projects?archived=true", headers=headers)
        assert rl_arch.status_code == 200
        archived = rl_arch.json()["projects"]
        assert len(archived) == 1
        assert archived[0]["id"] == pid2
        assert archived[0]["is_archived"] is True


# --- plan search -------------------------------------------------------


async def _create_plan(
    client, headers, project_id, title,
    html_content="<p>body</p>", frontmatter=None, is_public=False,
):
    r = await client.post(
        "/api/plans",
        json={
            "project_id": project_id,
            "title": title,
            "html_content": html_content,
            "frontmatter": frontmatter,
            "is_public": is_public,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# The search payload is metadata only: an Android launcher calls it on every
# keystroke, so `html_content` must never be present on any item.
PLAN_SUMMARY_KEYS = {
    "id", "project_id", "title", "slug", "url", "description",
    "is_public", "is_archived", "is_pinned", "created_at", "updated_at",
    "size_bytes",
}


@pytest.mark.asyncio
async def test_search_matches_title_case_insensitively():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch1@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        target = await _create_plan(client, headers, pid, "Quarterly Roadmap")
        await _create_plan(client, headers, pid, "Unrelated Notes")

        for term in ("quarterly", "QUARTERLY", "RoAdMaP"):
            r = await client.get("/api/plans/search", params={"q": term}, headers=headers)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["query"] == term
            assert [p["id"] for p in body["plans"]] == [target["id"]]
            assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_matches_slug_and_frontmatter_description():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch2@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        described = await _create_plan(
            client, headers, pid, "Untitled Alpha",
            frontmatter={"description": "Handles billing retries"},
        )
        await _create_plan(client, headers, pid, "Other Plan")

        # description match
        r = await client.get("/api/plans/search", params={"q": "RETRIES"}, headers=headers)
        assert r.status_code == 200, r.text
        assert [p["id"] for p in r.json()["plans"]] == [described["id"]]
        # slug match
        r = await client.get("/api/plans/search", params={"q": described["slug"]}, headers=headers)
        assert r.status_code == 200, r.text
        assert described["id"] in [p["id"] for p in r.json()["plans"]]
        # description is surfaced, and defaults to "" when absent
        hit = r.json()["plans"][0]
        assert hit["description"] == "Handles billing retries"


@pytest.mark.asyncio
async def test_search_description_defaults_to_empty_string():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch3@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        await _create_plan(client, headers, pid, "No Frontmatter")
        await _create_plan(client, headers, pid, "Empty Description", frontmatter={})

        r = await client.get("/api/plans/search", params={"q": ""}, headers=headers)
        assert r.status_code == 200, r.text
        assert len(r.json()["plans"]) == 2
        assert all(p["description"] == "" for p in r.json()["plans"])


@pytest.mark.asyncio
async def test_search_terms_are_anded():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch4@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        alpha = await _create_plan(
            client, headers, pid, "Alpha Migration",
            frontmatter={"description": "billing retries"},
        )
        beta = await _create_plan(
            client, headers, pid, "Beta Migration",
            frontmatter={"description": "storage cleanup"},
        )

        # Both terms hit the same plan -> it matches.
        r = await client.get(
            "/api/plans/search", params={"q": "migration billing"}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert [p["id"] for p in r.json()["plans"]] == [alpha["id"]]

        # "migration" hits both, "storage" only hits beta -> only beta survives.
        r = await client.get(
            "/api/plans/search", params={"q": "migration storage"}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert [p["id"] for p in r.json()["plans"]] == [beta["id"]]

        # No plan has both of these.
        r = await client.get(
            "/api/plans/search", params={"q": "alpha nonexistentterm"}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert r.json()["plans"] == []
        assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_excludes_archived_by_default():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch5@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        live = await _create_plan(client, headers, pid, "Live Plan")
        archived = await _create_plan(client, headers, pid, "Archived Plan")
        r = await client.post(f"/api/plans/{archived['id']}/archive", headers=headers)
        assert r.status_code == 200

        r = await client.get("/api/plans/search", params={"q": "plan"}, headers=headers)
        assert r.status_code == 200, r.text
        ids = [p["id"] for p in r.json()["plans"]]
        assert ids == [live["id"]]
        assert r.json()["total"] == 1

        r = await client.get(
            "/api/plans/search", params={"q": "plan", "include_archived": True}, headers=headers
        )
        assert r.status_code == 200, r.text
        ids = [p["id"] for p in r.json()["plans"]]
        assert sorted(ids) == sorted([live["id"], archived["id"]])
        assert r.json()["total"] == 2
        by_id = {p["id"]: p for p in r.json()["plans"]}
        assert by_id[live["id"]]["is_archived"] is False
        assert by_id[archived["id"]]["is_archived"] is True


@pytest.mark.asyncio
async def test_search_empty_query_returns_pinned_first():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch6@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        alpha = await _create_plan(client, headers, pid, "Alpha")
        zulu = await _create_plan(client, headers, pid, "Zulu")

        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["query"] == ""
        # Nothing pinned yet, so this is plain updated_at descending: Zulu was
        # created after Alpha.
        assert [p["title"] for p in body["plans"]] == ["Zulu", "Alpha"]
        assert all(p["is_pinned"] is False for p in body["plans"])

        # Pin the *older* plan. Pinned-first has to beat updated_at descending,
        # otherwise this assertion would pass without any pin logic at all.
        rpin = await client.post(f"/api/plans/{alpha['id']}/pin", headers=headers)
        assert rpin.status_code == 201

        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200, r.text
        plans = r.json()["plans"]
        assert [p["title"] for p in plans] == ["Alpha", "Zulu"]
        assert plans[0]["id"] == alpha["id"]
        assert plans[0]["is_pinned"] is True
        assert plans[1]["is_pinned"] is False

        # Blank whitespace is treated as "no text filter", not as a literal term.
        r = await client.get("/api/plans/search", params={"q": "   "}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["total"] == 2


@pytest.mark.asyncio
async def test_search_sorts_by_updated_at_descending():
    from httpx import AsyncClient, ASGITransport
    from main import app
    from db import Plan
    from datetime import datetime, timedelta, timezone
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch7@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        older = await _create_plan(client, headers, pid, "Alpha")
        newer = await _create_plan(client, headers, pid, "Zulu")

        base = datetime.now(timezone.utc) - timedelta(days=10)
        await Plan.filter(id=older["id"]).update(updated_at=base)
        await Plan.filter(id=newer["id"]).update(updated_at=base + timedelta(days=5))

        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200, r.text
        # Zulu is pinned-last alphabetically but updated most recently.
        assert [p["title"] for p in r.json()["plans"]] == ["Zulu", "Alpha"]

        # Same timestamp -> title ascending breaks the tie.
        await Plan.filter(id=newer["id"]).update(updated_at=base)
        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200, r.text
        assert [p["title"] for p in r.json()["plans"]] == ["Alpha", "Zulu"]


@pytest.mark.asyncio
async def test_search_limit_truncates_but_total_counts_all_matches():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch8@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        for i in range(5):
            await _create_plan(client, headers, pid, f"Widget Plan {i}")

        r = await client.get("/api/plans/search", params={"q": "widget"}, headers=headers)
        assert r.status_code == 200, r.text
        assert len(r.json()["plans"]) == 5
        assert r.json()["total"] == 5

        r = await client.get(
            "/api/plans/search", params={"q": "widget", "limit": 2}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["plans"]) == 2
        assert r.json()["total"] == 5

        # limit is clamped, not rejected: 0 -> 1, 9999 -> 200.
        r = await client.get(
            "/api/plans/search", params={"q": "widget", "limit": 0}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["plans"]) == 1
        assert r.json()["total"] == 5

        r = await client.get(
            "/api/plans/search", params={"q": "widget", "limit": 9999}, headers=headers
        )
        assert r.status_code == 200, r.text
        assert len(r.json()["plans"]) == 5


@pytest.mark.asyncio
async def test_search_requires_authentication():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/plans/search", params={"q": "anything"})
        assert r.status_code == 401

        r = await client.get(
            "/api/plans/search", params={"q": "anything"},
            headers={"Authorization": "Bearer plan_bogus_key"},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_search_items_never_include_html_content():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch9@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        body = "<html>" + ("<p>filler</p>" * 500) + "</html>"
        created = await _create_plan(
            client, headers, pid, "Heavy Plan", html_content=body,
            frontmatter={"description": "big one"}, is_public=True,
        )

        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200, r.text
        plans = r.json()["plans"]
        assert len(plans) == 1
        item = plans[0]

        assert "html_content" not in item
        assert set(item.keys()) == PLAN_SUMMARY_KEYS
        assert item["id"] == created["id"]
        assert item["project_id"] == pid
        assert item["title"] == "Heavy Plan"
        assert item["slug"] == created["slug"]
        assert item["url"] == f"/p/{created['slug']}"
        assert item["description"] == "big one"
        assert item["is_public"] is True
        assert item["is_archived"] is False
        assert item["is_pinned"] is False
        assert item["created_at"]
        assert item["updated_at"]
        assert item["size_bytes"] == len(body)
        # The response body is metadata only, not the megabyte HTML.
        assert body not in r.text


@pytest.mark.asyncio
async def test_search_does_not_shadow_plan_id_route():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "srch10@example.com")
        rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
        pid = rp.json()["id"]
        created = await _create_plan(client, headers, pid, "Route Check", html_content="<p>xy</p>")

        # "/search" must not be swallowed by the /{plan_id} path parameter,
        # which would answer 400 "Invalid plan_id format".
        r = await client.get("/api/plans/search", params={"q": "route"}, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["query"] == "route"
        assert body["total"] == 1
        assert body["plans"][0]["id"] == created["id"]
        assert set(body) == {"plans", "total", "query"}

        # The real plan-id route still resolves, body included.
        rg = await client.get(f"/api/plans/{created['id']}", headers=headers)
        assert rg.status_code == 200, rg.text
        assert rg.json()["html_content"] == "<p>xy</p>"

        # A genuinely malformed id is still rejected as before.
        rbad = await client.get("/api/plans/not-a-uuid", headers=headers)
        assert rbad.status_code == 400
        assert "Invalid plan_id format" in rbad.json()["detail"]


@pytest.mark.asyncio
async def test_search_scoped_to_caller_and_project():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h1 = await _register_and_get_headers(client, "srch11a@example.com")
        h2 = await _register_and_get_headers(client, "srch11b@example.com")

        proj_a = (await client.post("/api/projects", json={"name": "A"}, headers=h1)).json()["id"]
        proj_b = (await client.post("/api/projects", json={"name": "B"}, headers=h1)).json()["id"]
        mine_a = await _create_plan(client, h1, proj_a, "Shared Term Alpha")
        mine_b = await _create_plan(client, h1, proj_b, "Shared Term Beta")

        # Another user owns a plan with the same matching term.
        other_proj = (await client.post("/api/projects", json={"name": "Theirs"}, headers=h2)).json()["id"]
        await _create_plan(client, h2, other_proj, "Shared Term Gamma")

        r = await client.get("/api/plans/search", params={"q": "shared"}, headers=h1)
        assert r.status_code == 200, r.text
        ids = {p["id"] for p in r.json()["plans"]}
        assert ids == {mine_a["id"], mine_b["id"]}

        r = await client.get(
            "/api/plans/search", params={"q": "shared", "project_id": proj_b}, headers=h1
        )
        assert r.status_code == 200, r.text
        assert [p["id"] for p in r.json()["plans"]] == [mine_b["id"]]

        # An unknown project filter simply matches nothing.
        r = await client.get(
            "/api/plans/search",
            params={"q": "shared", "project_id": "00000000-0000-0000-0000-000000000000"},
            headers=h1,
        )
        assert r.status_code == 200, r.text
        assert r.json()["plans"] == []
        assert r.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/plans/search
#
# Search returns plan metadata only. The whole point of the endpoint is that a
# client can search an account without downloading every html_content body.
# ---------------------------------------------------------------------------


async def _make_plan(client, headers, project_id, title, html="<p>x</p>", **extra):
    payload = {"project_id": project_id, "title": title, "html_content": html}
    payload.update(extra)
    r = await client.post("/api/plans", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_search_finds_plan_by_title_case_insensitively():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search1@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        await _make_plan(client, headers, pid, "Berlin Weekend")

        r = await client.get("/api/plans/search?q=BERLIN", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["query"] == "BERLIN"
        assert body["plans"][0]["title"] == "Berlin Weekend"
        assert body["plans"][0]["url"] == "/p/berlin-weekend"


@pytest.mark.asyncio
async def test_search_finds_plan_by_frontmatter_description():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search2@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        await _make_plan(
            client, headers, pid, "Untitled trip",
            frontmatter={"description": "Three days around the Museumsinsel"},
        )

        r = await client.get("/api/plans/search?q=museumsinsel", headers=headers)
        assert r.status_code == 200
        plans = r.json()["plans"]
        assert len(plans) == 1
        assert plans[0]["description"] == "Three days around the Museumsinsel"


@pytest.mark.asyncio
async def test_search_ands_multiple_terms():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search3@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        await _make_plan(client, headers, pid, "Berlin weekend")
        await _make_plan(client, headers, pid, "Paris long weekend")
        await _make_plan(client, headers, pid, "Berlin city break")

        both = await client.get("/api/plans/search?q=berlin%20weekend", headers=headers)
        titles = sorted(p["title"] for p in both.json()["plans"])
        assert titles == ["Berlin weekend"]

        # A term nobody matches yields nothing rather than an OR.
        nothing = await client.get("/api/plans/search?q=berlin%20atlantis", headers=headers)
        assert nothing.json()["plans"] == []
        assert nothing.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_excludes_archived_by_default():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search4@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        plan = await _make_plan(client, headers, pid, "Old itinerary")
        await client.post(f"/api/plans/{plan['id']}/archive", headers=headers)

        default = await client.get("/api/plans/search?q=itinerary", headers=headers)
        assert default.json()["plans"] == []

        included = await client.get(
            "/api/plans/search?q=itinerary&include_archived=true", headers=headers
        )
        assert included.json()["total"] == 1
        assert included.json()["plans"][0]["is_archived"] is True


@pytest.mark.asyncio
async def test_search_empty_query_lists_pinned_first():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search5@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        await _make_plan(client, headers, pid, "Alpha")
        pinned = await _make_plan(client, headers, pid, "Zulu")
        await client.post(f"/api/plans/{pinned['id']}/pin", headers=headers)

        r = await client.get("/api/plans/search", headers=headers)
        assert r.status_code == 200
        plans = r.json()["plans"]
        assert [p["title"] for p in plans] == ["Zulu", "Alpha"]
        assert plans[0]["is_pinned"] is True
        assert plans[1]["is_pinned"] is False


@pytest.mark.asyncio
async def test_search_limit_truncates_but_total_reports_all_matches():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search6@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        for i in range(5):
            await _make_plan(client, headers, pid, f"Itinerary {i}")

        r = await client.get("/api/plans/search?q=itinerary&limit=2", headers=headers)
        body = r.json()
        assert len(body["plans"]) == 2
        assert body["total"] == 5


@pytest.mark.asyncio
async def test_search_requires_authentication():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/plans/search?q=anything")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_search_response_never_contains_html_content():
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search7@example.com")
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        await _make_plan(client, headers, pid, "Secret document", html="<p>super secret</p>")

        r = await client.get("/api/plans/search?q=secret", headers=headers)
        assert "super secret" not in r.text
        plan = r.json()["plans"][0]
        assert "html_content" not in plan
        # The length is still reported, so clients can show a size.
        assert plan["size_bytes"] == len("<p>super secret</p>")


@pytest.mark.asyncio
async def test_search_route_does_not_shadow_get_plan():
    """`/search` must not be captured by the `/{plan_id}` route."""
    from httpx import AsyncClient, ASGITransport
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _register_and_get_headers(client, "search8@example.com")

        found = await client.get("/api/plans/search?q=x", headers=headers)
        assert found.status_code == 200
        assert found.json()["plans"] == []

        # The pre-existing single-plan route must still behave.
        rp = await client.post("/api/projects", json={"name": "Trips"}, headers=headers)
        pid = rp.json()["id"]
        plan = await _make_plan(client, headers, pid, "Still works")

        one = await client.get(f"/api/plans/{plan['id']}", headers=headers)
        assert one.status_code == 200
        assert one.json()["title"] == "Still works"
        # ...and it still carries the body the search endpoint withholds.
        assert one.json()["html_content"] == "<p>x</p>"
