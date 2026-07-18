import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from tortoise import Tortoise

from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from routes.page import router as page_router

from models import Plan

# Absolute paths so templates/static resolve correctly on Vercel (cwd may differ).
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await Tortoise.init(config=TORTOISE_ORM)
    except Exception as exc:
        import logging
        logging.getLogger("main").warning("Tortoise init failed: %s", exc)
    yield
    try:
        await Tortoise.close_connections()
    except Exception:
        pass


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
