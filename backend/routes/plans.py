import re
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from db import User, Project, Plan, PlanPin
from routes.auth import get_current_user

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50].strip("-") or f"plan-{uuid.uuid4().hex[:8]}"


async def _get_user_plan(plan_id: str, user: User):
    user_project_ids = await Project.filter(user_id=user.id).values_list("id", flat=True)
    return await Plan.filter(id=plan_id, project_id__in=list(user_project_ids)).first()


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
    is_approved: bool
    is_pinned: bool = False
    approved_at: Optional[str]
    approved_by: Optional[str]
    created_at: str
    updated_at: str


class PlanListResponse(BaseModel):
    plans: List[PlanResponse]


def to_response(p: Plan, is_pinned: bool = False) -> PlanResponse:
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
        is_approved=p.is_approved,
        is_pinned=is_pinned,
        approved_at=p.approved_at.isoformat() if p.approved_at else None,
        approved_by=p.approved_by,
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

    user_project_ids = await Project.filter(user_id=user.id).values_list("id", flat=True)
    query = Plan.filter(project_id__in=list(user_project_ids))
    if project_id:
        query = query.filter(project_id=project_id)

    plans = await query.all()
    
    pinned_plan_ids = set(
        await PlanPin.filter(user_id=user.id).values_list("plan_id", flat=True)
    )
    
    plan_responses = []
    for p in plans:
        plan_responses.append(to_response(p, is_pinned=str(p.id) in pinned_plan_ids))
    
    plan_responses.sort(key=lambda r: (not r.is_pinned, r.title))
    
    return PlanListResponse(plans=plan_responses)


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

    plan = await Plan.create(
        project_id=project.id,
        title=request.title,
        slug=slug,
        html_content=request.html_content,
        frontmatter=request.frontmatter,
        is_public=request.is_public,
    )

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

    plan = await _get_user_plan(plan_id, user)
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

    plan = await _get_user_plan(plan_id, user)
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

    plan = await _get_user_plan(plan_id, user)
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

    plan = await _get_user_plan(plan_id, user)
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

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_public = False
    await plan.save()

    return to_response(plan)


@router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_approved = True
    plan.approved_at = datetime.utcnow()
    plan.approved_by = user.email
    await plan.save()

    return to_response(plan)


@router.post("/{plan_id}/unapprove", response_model=PlanResponse)
async def unapprove_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_approved = False
    plan.approved_at = None
    plan.approved_by = None
    await plan.save()

    return to_response(plan)


@router.post("/{plan_id}/pin", response_model=PlanResponse, status_code=201)
async def pin_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    existing = await PlanPin.filter(user_id=user.id, plan_id=plan.id).first()
    if existing:
        return to_response(plan, is_pinned=True)

    await PlanPin.create(user_id=user.id, plan_id=plan.id)
    return to_response(plan, is_pinned=True)


@router.delete("/{plan_id}/pin", status_code=204)
async def unpin_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await PlanPin.filter(user_id=user.id, plan_id=plan.id).delete()


@router.post("/{plan_id}/archive", response_model=PlanResponse)
async def archive_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_archived = True
    await plan.save()
    return to_response(plan)


@router.post("/{plan_id}/unarchive", response_model=PlanResponse)
async def unarchive_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_archived = False
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

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await plan.delete()
