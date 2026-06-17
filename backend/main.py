from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise
from tortoise_conf import TORTOISE_ORM
from routes.auth import router as auth_router
from routes.projects import router as projects_router
from routes.plans import router as plans_router
from models import Plan

app = FastAPI(title="HTML Plan Service")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(plans_router, prefix="/api/plans", tags=["plans"])


@app.get("/p/{slug}", response_class=HTMLResponse)
async def serve_public_plan(slug: str):
    plan = await Plan.filter(slug=slug, is_public=True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    title = plan.title
    description = ""
    if plan.frontmatter:
        description = plan.frontmatter.get("description", "")
    
    html = plan.html_content
    
    if "<head>" in html:
        meta_tags = f"""
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
"""
        html = html.replace("<head>", f"<head>{meta_tags}")
    
    return HTMLResponse(content=html)


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)
