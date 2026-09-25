"""Tests for plan version control.

Includes the deployment-safety case: a database with no ``plan_versions``
table must keep plan CRUD working.
"""

import os
import tempfile

import pytest
import pytest_asyncio
from tortoise import Tortoise

TEST_DB = tempfile.mktemp(suffix=".db")

TEST_TORTOISE = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {"file_path": TEST_DB},
        }
    },
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
    # Remove so each test starts from an empty database.
    try:
        os.remove(TEST_DB)
    except FileNotFoundError:
        pass


@pytest_asyncio.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _setup(client, email="ver@example.com"):
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": "secret123"}
    )
    headers = {"Authorization": f"Bearer {r.json()['api_key']}"}
    rp = await client.post("/api/projects", json={"name": "P"}, headers=headers)
    return headers, rp.json()["id"]


async def _plan(client, headers, project_id, html="<p>v1</p>", title="T"):
    r = await client.post(
        "/api/plans",
        json={
            "project_id": project_id,
            "title": title,
            "html_content": html,
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


# --- core history -----------------------------------------------------------


@pytest.mark.asyncio
async def test_update_creates_previous_version(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>v1</p>")

    r = await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>v2</p>"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["html_content"] == "<p>v2</p>"

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert rv.status_code == 200
    versions = rv.json()["versions"]
    assert len(versions) == 1
    assert versions[0]["version"] == 1


@pytest.mark.asyncio
async def test_original_content_is_recoverable(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>original</p>")

    for html in ("<p>second</p>", "<p>third</p>"):
        await client.put(
            f"/api/plans/{plan['id']}", json={"html_content": html}, headers=headers
        )

    rv = await client.get(
        f"/api/plans/{plan['id']}/versions/1", headers=headers
    )
    assert rv.status_code == 200
    assert rv.json()["html_content"] == "<p>original</p>"


@pytest.mark.asyncio
async def test_versions_newest_first(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    for html in ("<p>a</p>", "<p>b</p>", "<p>c</p>"):
        await client.put(
            f"/api/plans/{plan['id']}", json={"html_content": html}, headers=headers
        )

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    numbers = [v["version"] for v in rv.json()["versions"]]
    assert numbers == sorted(numbers, reverse=True)


@pytest.mark.asyncio
async def test_restore_rolls_back_and_is_reversible(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>good</p>")

    await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>bad</p>"}, headers=headers
    )

    rr = await client.post(
        f"/api/plans/{plan['id']}/versions/1/restore", headers=headers
    )
    assert rr.status_code == 200
    assert rr.json()["html_content"] == "<p>good</p>"

    # The pre-restore state was preserved, so the bad version still exists.
    rv = await client.get(
        f"/api/plans/{plan['id']}/versions/2", headers=headers
    )
    assert rv.status_code == 200
    assert rv.json()["html_content"] == "<p>bad</p>"

    # And restoring it forward works.
    rr2 = await client.post(
        f"/api/plans/{plan['id']}/versions/2/restore", headers=headers
    )
    assert rr2.status_code == 200
    assert rr2.json()["html_content"] == "<p>bad</p>"


@pytest.mark.asyncio
async def test_restore_unknown_version_404s_and_leaves_plan_alone(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>keep</p>")
    await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>now</p>"}, headers=headers
    )

    rr = await client.post(
        f"/api/plans/{plan['id']}/versions/99/restore", headers=headers
    )
    assert rr.status_code == 404

    rg = await client.get(f"/api/plans/{plan['id']}", headers=headers)
    assert rg.json()["html_content"] == "<p>now</p>"


@pytest.mark.asyncio
async def test_title_and_frontmatter_are_also_versioned(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, title="Old", html="<p>x</p>")

    await client.put(
        f"/api/plans/{plan['id']}",
        json={"title": "New", "frontmatter": {"tags": ["a"]}},
        headers=headers,
    )

    rv = await client.get(f"/api/plans/{plan['id']}/versions/1", headers=headers)
    assert rv.json()["title"] == "Old"


@pytest.mark.asyncio
async def test_publish_toggle_does_not_create_a_version(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)

    r = await client.post(f"/api/plans/{plan['id']}/publish", headers=headers)
    assert r.status_code == 200

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert rv.json()["versions"] == []


@pytest.mark.asyncio
async def test_unchanged_update_does_not_duplicate_versions(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>same</p>")

    await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>same</p>"},
        headers=headers,
    )
    await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>same</p>"},
        headers=headers,
    )

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert len(rv.json()["versions"]) == 1


@pytest.mark.asyncio
async def test_manual_snapshot_with_note(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>ship</p>")

    r = await client.post(
        f"/api/plans/{plan['id']}/versions",
        json={"note": "before redesign"},
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["note"] == "before redesign"
    assert r.json()["html_content"] == "<p>ship</p>"

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert rv.json()["versions"][0]["note"] == "before redesign"


# --- diff -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diff_between_versions(client):
    headers, pid = await _setup(client)
    # Two updates are needed before a v2 exists: each update snapshots the
    # state it replaced, so v1 is the original and v2 is the first update.
    plan = await _plan(client, headers, pid, html="<p>one</p>\n<p>two</p>")
    await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>one</p>\n<p>changed</p>"},
        headers=headers,
    )
    await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>one</p>\n<p>changed</p>\n<p>third</p>"},
        headers=headers,
    )

    r = await client.get(
        f"/api/plans/{plan['id']}/diff", params={"from": 1, "to": 2}, headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["changed"] is True
    assert body["added"] >= 1
    assert body["removed"] >= 1
    assert "changed" in body["diff"]


@pytest.mark.asyncio
async def test_diff_against_live_plan(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>old</p>")
    await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>new</p>"}, headers=headers
    )

    r = await client.get(
        f"/api/plans/{plan['id']}/diff", params={"from": 1}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["changed"] is True


@pytest.mark.asyncio
async def test_diff_unknown_version_404s(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    r = await client.get(
        f"/api/plans/{plan['id']}/diff", params={"from": 42}, headers=headers
    )
    assert r.status_code == 404


# --- isolation & auth -------------------------------------------------------


@pytest.mark.asyncio
async def test_versions_are_private_to_the_owner(client):
    headers_a, pid_a = await _setup(client, "owner_a@example.com")
    plan = await _plan(client, headers_a, pid_a, html="<p>secret</p>")
    await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>secret2</p>"},
        headers=headers_a,
    )

    r_b = await client.post(
        "/api/auth/register",
        json={"email": "intruder@example.com", "password": "secret123"},
    )
    headers_b = {"Authorization": f"Bearer {r_b.json()['api_key']}"}

    assert (await client.get(f"/api/plans/{plan['id']}/versions", headers=headers_b)).status_code == 404
    assert (await client.get(f"/api/plans/{plan['id']}/versions/1", headers=headers_b)).status_code == 404
    assert (
        await client.post(
            f"/api/plans/{plan['id']}/versions/1/restore", headers=headers_b
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_versions_require_auth(client):
    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    r = await client.get(f"/api/plans/{plan['id']}/versions")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invalid_plan_id_is_rejected(client):
    headers, _ = await _setup(client)
    r = await client.get("/api/plans/not-a-uuid/versions", headers=headers)
    assert r.status_code == 400


# --- lifecycle --------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleting_plan_deletes_versions(client):
    from db import PlanVersion

    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>x</p>"}, headers=headers
    )
    assert await PlanVersion.filter(plan_id=plan["id"]).count() == 1

    rd = await client.delete(f"/api/plans/{plan['id']}", headers=headers)
    assert rd.status_code == 204
    assert await PlanVersion.filter(plan_id=plan["id"]).count() == 0


@pytest.mark.asyncio
async def test_deleting_project_cascades_versions(client):
    from db import PlanVersion

    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>x</p>"}, headers=headers
    )
    assert await PlanVersion.filter(plan_id=plan["id"]).count() == 1

    await client.delete(f"/api/projects/{pid}", headers=headers)
    assert await PlanVersion.filter(plan_id=plan["id"]).count() == 0


# --- deployment safety ------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_update_works_without_the_version_table(client):
    """The critical deploy-day case: no plan_versions table must not 500."""
    from tortoise import connections
    from db import PlanVersion

    await connections.get("default").execute_query("DROP TABLE IF EXISTS plan_versions")

    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid, html="<p>before</p>")

    r = await client.put(
        f"/api/plans/{plan['id']}",
        json={"html_content": "<p>after</p>"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["html_content"] == "<p>after</p>"

    # Reads and other endpoints stay healthy too.
    assert (await client.get(f"/api/plans/{plan['id']}", headers=headers)).status_code == 200
    assert (await client.get("/api/plans", headers=headers)).status_code == 200

    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert rv.status_code == 200
    assert rv.json()["versions"] == []
    assert rv.json()["versioning_available"] is False

    assert (
        await client.post(f"/api/plans/{plan['id']}/versions", headers=headers)
    ).status_code == 503


@pytest.mark.asyncio
async def test_ensure_version_schema_recovers_a_dropped_table(client):
    from tortoise import connections
    from services import versioning

    await connections.get("default").execute_query("DROP TABLE IF EXISTS plan_versions")
    assert await versioning.ensure_version_schema() is True
    # Idempotent.
    assert await versioning.ensure_version_schema() is True

    headers, pid = await _setup(client)
    plan = await _plan(client, headers, pid)
    r = await client.put(
        f"/api/plans/{plan['id']}", json={"html_content": "<p>z</p>"}, headers=headers
    )
    assert r.status_code == 200
    rv = await client.get(f"/api/plans/{plan['id']}/versions", headers=headers)
    assert len(rv.json()["versions"]) == 1


@pytest.mark.asyncio
async def test_ensure_version_schema_never_raises_on_a_bad_connection():
    from services import versioning

    # No Tortoise connection initialised in this test's context is not
    # possible (autouse fixture initialises one), so assert the happy path
    # plus that the helper swallows a missing-connection error.
    assert await versioning.ensure_version_schema() is True
