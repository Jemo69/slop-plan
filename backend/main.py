import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from tortoise.contrib.fastapi import register_tortoise

from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from models import Plan

app = FastAPI(
    title="HTML Plan Service",
    version="0.1.0",
    description="Service to store and serve HTML plans",
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


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "html-plan-service", "version": "0.1.0"}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


@app.get("/p/{slug}", response_class=HTMLResponse, tags=["public"])
async def serve_public_plan(slug: str):
    plan = await Plan.filter(slug=slug, is_public=True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    title = plan.title
    description = ""
    if plan.frontmatter:
        description = plan.frontmatter.get("description", "") or ""

    html = plan.html_content

    if "<head>" in html.lower():
        safe_title = title.replace('"', "&quot;")
        safe_desc = description.replace('"', "&quot;")
        meta_tags = f'''
    <meta property="og:title" content="{safe_title}">
    <meta property="og:description" content="{safe_desc}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{safe_title}">
    <meta name="twitter:description" content="{safe_desc}">
'''
        lower = html.lower()
        head_idx = lower.find("<head>")
        if head_idx != -1:
            insert_pos = head_idx + len("<head>")
            html = html[:insert_pos] + meta_tags + html[insert_pos:]

    return HTMLResponse(content=html)


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)
