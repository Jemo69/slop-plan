import re
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from models import User, Project, Plan
from routes.auth import get_current_user

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50].strip("-") or f"plan-{uuid.uuid4().hex[:8]}"


class PlanCreate(BaseModel):
    project_id: str
    title: str
    html_content: str
    frontmatter: Optional[dict] = None
    is_public: bool = False


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    html_content: Optional[str] = None
    frontmatter: Optional[dict] = None
    is_public: Optional[bool] = None


class PlanResponse(BaseModel):
    id: str
    project_id: str
    title: str
    slug: str
    url: str
    html_content: str
    frontmatter: Optional[dict]
    is_public: bool
    created_at: str
    updated_at: str


class PlanListResponse(BaseModel):
    plans: List[PlanResponse]


def to_response(p: Plan) -> PlanResponse:
    pid = str(p.project_id) if hasattr(p, "project_id") else ""
    if not pid and hasattr(p, "project"):
        try:
            pid = str(p.project.id) if hasattr(p.project, "id") else ""
        except Exception:
            pid = ""
    return PlanResponse(
        id=str(p.id),
        project_id=pid,
        title=p.title,
        slug=p.slug,
        url=f"/p/{p.slug}",
        html_content=p.html_content,
        frontmatter=p.frontmatter,
        is_public=p.is_public,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


@router.get("", response_model=PlanListResponse)
async def list_plans(
    project_id: Optional[str] = Query(None),
    public: Optional[bool] = Query(None, description="filter public plans"),
    user: User = Depends(get_current_user),
):
    if public:
        query = Plan.filter(is_public=True)
        if project_id:
            query = query.filter(project_id=project_id)
        plans = await query.all()
        return PlanListResponse(plans=[to_response(p) for p in plans])

    query = Plan.filter(project__user_id=user.id)
    if project_id:
        query = query.filter(project_id=project_id)

    plans = await query.all()
    return PlanListResponse(plans=[to_response(p) for p in plans])


@router.get("/public", response_model=PlanListResponse)
async def list_public_plans():
    plans = await Plan.filter(is_public=True).all()
    return PlanListResponse(plans=[to_response(p) for p in plans])


@router.post("", response_model=PlanResponse, status_code=201)
async def create_plan(
    request: PlanCreate,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = await Project.filter(id=request.project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    base_slug = slugify(request.title)
    slug = base_slug
    counter = 1
    while await Plan.filter(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    try:
        plan = await Plan.create(
            project_id=project.id,
            title=request.title,
            slug=slug,
            html_content=request.html_content,
            frontmatter=request.frontmatter,
            is_public=request.is_public,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    return to_response(plan)


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await Plan.filter(id=plan_id, project__user_id=user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return to_response(plan)


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    request: PlanUpdate,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await Plan.filter(id=plan_id, project__user_id=user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if request.title is not None:
        plan.title = request.title
    if request.html_content is not None:
        plan.html_content = request.html_content
    if request.frontmatter is not None:
        plan.frontmatter = request.frontmatter
    if request.is_public is not None:
        plan.is_public = request.is_public

    await plan.save()

    return to_response(plan)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await Plan.filter(id=plan_id, project__user_id=user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await plan.delete()


@router.post("/{plan_id}/publish", response_model=PlanResponse)
async def publish_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await Plan.filter(id=plan_id, project__user_id=user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_public = True
    await plan.save()

    return to_response(plan)


@router.post("/{plan_id}/unpublish", response_model=PlanResponse)
async def unpublish_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await Plan.filter(id=plan_id, project__user_id=user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_public = False
    await plan.save()

    return to_response(plan)
