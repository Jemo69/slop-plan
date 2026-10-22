import asyncio
import logging
import os
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

_APP_DIR = str(Path(__file__).resolve().parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

_vendor_path = os.path.join(_APP_DIR, "_vendor")
if os.path.exists(_vendor_path) and _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from tortoise import connections
from tortoise.contrib.fastapi import RegisterTortoise
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from routes.page import router as page_router
from services import versioning


# Absolute paths so templates/static resolve correctly on Vercel (cwd may differ).
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


_db_initialized = False

# Database health, tracked so a broken database fails fast instead of hanging.
_db_state: dict[str, object] = {
    "unavailable": False,
    "reason": "",
    "checked_at": 0.0,
}

# A cold start must never take long, so the probe window is short. It only has
# to notice a database that blocks forever, not to diagnose it.
DB_PROBE_TIMEOUT = 5.0

# How long the API stays disabled before it tries the database again, and how
# long that retry may take. A transient blip must not disable the API for the
# whole life of a warm instance.
DB_RECHECK_INTERVAL = 30.0
DB_RECHECK_TIMEOUT = 2.0

_PROBE_SQL = "SELECT name FROM sqlite_master LIMIT 1"


async def _database_answers(timeout: float) -> bool:
    """Return True when the database replies within the timeout.

    A hang means False. A regular error means True: the database did answer,
    so the request can surface that error instead of a gateway timeout.
    """
    try:
        await asyncio.wait_for(
            connections.get("default").execute_query(_PROBE_SQL),
            timeout=timeout,
        )
        return True
    except asyncio.TimeoutError:
        return False
    except Exception:  # noqa: BLE001 - a probe failure must not kill the boot
        return True


async def _probe_database() -> None:
    """Detect a database that hangs, before a user request pays for it.

    A deployment that is missing its Turso credentials falls back to the local
    SQLite file. The Vercel filesystem is read-only, so the first real query
    blocks forever and the request dies as a 504 after the function timeout
    (30s), with nothing in the logs but a timeout. Probing once at startup
    turns that into an immediate 503 with a readable reason.
    """
    _db_state["checked_at"] = time.monotonic()
    if await _database_answers(DB_PROBE_TIMEOUT):
        return

    _db_state["unavailable"] = True
    _db_state["reason"] = (
        f"database probe timed out after {DB_PROBE_TIMEOUT}s; "
        "check DATABASE_URL and TURSO_AUTH_TOKEN"
    )
    logging.getLogger(__name__).error("database unavailable: %s", _db_state["reason"])


async def _recheck_database() -> None:
    """Retry the database periodically so a transient blip heals itself."""
    now = time.monotonic()
    if now - float(_db_state["checked_at"]) < DB_RECHECK_INTERVAL:
        return

    _db_state["checked_at"] = now
    if await _database_answers(DB_RECHECK_TIMEOUT):
        _db_state["unavailable"] = False
        _db_state["reason"] = ""
        logging.getLogger(__name__).info("database recovered")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not _db_initialized:
        async with RegisterTortoise(
            app,
            config=TORTOISE_ORM,
        ):
            # Vercel never runs migrations for this service, so bring the
            # version table up to date here. Idempotent and fail-soft: a
            # problem here must never take down a cold start.
            await versioning.ensure_version_schema()
            await _probe_database()
            yield
    else:
        yield


app = FastAPI(
    title="Slop Plans",
    version="0.1.0",
    description="Service to store and serve HTML plans",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def database_guard(request, call_next):
    """Answer API calls with 503 while the database is known to be unusable.

    Without this, a broken database blocks each request until the platform
    kills the function, so the caller only ever sees a gateway timeout.
    """
    if _db_state["unavailable"] and request.url.path.startswith("/api/"):
        await _recheck_database()
        if _db_state["unavailable"]:
            return JSONResponse(
                status_code=503,
                content={"detail": "database unavailable"},
                headers={"Retry-After": "5"},
            )
    return await call_next(request)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(plans_router, prefix="/api/plans", tags=["plans"])
app.include_router(page_router, tags=["page"])

# Conditional mount: missing dirs must not crash serverless cold starts.
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = (
    Jinja2Templates(directory=str(TEMPLATES_DIR)) if TEMPLATES_DIR.is_dir() else None
)
