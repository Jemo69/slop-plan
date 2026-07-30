from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Response

from db import Plan

templates: Jinja2Templates | None = Jinja2Templates(directory="templates")

router = APIRouter()


@router.get("/health", tags=["health"])
async def root():
    return {"status": "ok", "service": "html-plan-service", "version": "0.1.0"}


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@router.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def dashboard(request: Request):
    return _require_templates().TemplateResponse(request, "dashboard.html")


NAV_BAR = """<div style="position:fixed;top:0;left:0;right:0;z-index:9999;display:flex;align-items:center;justify-content:space-between;padding:10px 20px;background:#1a1a2e;border-bottom:1px solid #333;">
  <a href="/dashboard" style="color:#6c5ce7;text-decoration:none;font-size:14px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">&larr; Dashboard</a>
</div>"""

BODY_PADDING = "<style>body{padding-top:48px!important}</style>"


@router.get("/p/{slug}", response_class=HTMLResponse, tags=["public"])
async def serve_public_plan(slug: str):
    plan = await Plan.filter(slug=slug, is_public=True, is_archived=False).first()
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

    lower = html.lower()
    body_idx = lower.find("<body>")
    if body_idx != -1:
        insert_pos = body_idx + len("<body>")
        html = html[:insert_pos] + NAV_BAR + BODY_PADDING + html[insert_pos:]
    else:
        html = NAV_BAR + html

    return HTMLResponse(content=html)


def _require_templates() -> Jinja2Templates:
    if templates is None:
        raise HTTPException(status_code=500, detail="Templates not configured")
    return templates


@router.get("/", response_class=HTMLResponse, tags=["templates"])
@router.get("/app", response_class=HTMLResponse, tags=["templates"])
async def template_home(request: Request):
    return _require_templates().TemplateResponse(request, "index.html")
