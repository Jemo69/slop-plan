import asyncio
import logging
import os
import sys
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
from tortoise.contrib.fastapi import RegisterTortoise
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from routes.page import router as page_router


# Absolute paths so templates/static resolve correctly on Vercel (cwd may differ).
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


_db_initialized = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not _db_initialized:
        async with RegisterTortoise(
            app,
            config=TORTOISE_ORM,
        ):
            yield
    else:
        yield


app = FastAPI(
    title="HTML Plan Service",
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
