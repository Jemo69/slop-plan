import re
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from models import User, Project, Plan
from routes.auth import get_current_user

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50]


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


@router.get("", response_model=PlanListResponse)
async def list_plans(
    project_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    query = Plan.filter(project__user=user)
    if project_id:
        query = query.filter(project_id=project_id)

    plans = await query.all()
    return PlanListResponse(
        plans=[
            PlanResponse(
                id=str(p.id),
                project_id=str(p.project_id),
                title=p.title,
                slug=p.slug,
                url=f"/p/{p.slug}",
                html_content=p.html_content,
                frontmatter=p.frontmatter,
                is_public=p.is_public,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in plans
        ]
    )


@router.get("/public", response_model=PlanListResponse)
async def list_public_plans():
    plans = await Plan.filter(is_public=True).all()
    return PlanListResponse(
        plans=[
            PlanResponse(
                id=str(p.id),
                project_id=str(p.project_id),
                title=p.title,
                slug=p.slug,
                url=f"/p/{p.slug}",
                html_content=p.html_content,
                frontmatter=p.frontmatter,
                is_public=p.is_public,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in plans
        ]
    )


@router.post("", response_model=PlanResponse, status_code=201)
async def create_plan(
    request: PlanCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.filter(id=request.project_id, user=user).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    base_slug = slugify(request.title)
    slug = base_slug
    counter = 1
    while await Plan.filter(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    plan = await Plan.create(
        project=project,
        title=request.title,
        slug=slug,
        html_content=request.html_content,
        frontmatter=request.frontmatter,
        is_public=request.is_public,
    )

    return PlanResponse(
        id=str(plan.id),
        project_id=str(plan.project_id),
        title=plan.title,
        slug=plan.slug,
        url=f"/p/{plan.slug}",
        html_content=plan.html_content,
        frontmatter=plan.frontmatter,
        is_public=plan.is_public,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    plan = await Plan.filter(id=plan_id, project__user=user).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        id=str(plan.id),
        project_id=str(plan.project_id),
        title=plan.title,
        slug=plan.slug,
        url=f"/p/{plan.slug}",
        html_content=plan.html_content,
        frontmatter=plan.frontmatter,
        is_public=plan.is_public,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    request: PlanUpdate,
    user: User = Depends(get_current_user),
):
    plan = await Plan.filter(id=plan_id, project__user=user).first()
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

    return PlanResponse(
        id=str(plan.id),
        project_id=str(plan.project_id),
        title=plan.title,
        slug=plan.slug,
        url=f"/p/{plan.slug}",
        html_content=plan.html_content,
        frontmatter=plan.frontmatter,
        is_public=plan.is_public,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    plan = await Plan.filter(id=plan_id, project__user=user).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    await plan.delete()


@router.post("/{plan_id}/publish", response_model=PlanResponse)
async def publish_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    plan = await Plan.filter(id=plan_id, project__user=user).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_public = True
    await plan.save()

    return PlanResponse(
        id=str(plan.id),
        project_id=str(plan.project_id),
        title=plan.title,
        slug=plan.slug,
        url=f"/p/{plan.slug}",
        html_content=plan.html_content,
        frontmatter=plan.frontmatter,
        is_public=plan.is_public,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


@router.post("/{plan_id}/unpublish", response_model=PlanResponse)
async def unpublish_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    plan = await Plan.filter(id=plan_id, project__user=user).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_public = False
    await plan.save()

    return PlanResponse(
        id=str(plan.id),
        project_id=str(plan.project_id),
        title=plan.title,
        slug=plan.slug,
        url=f"/p/{plan.slug}",
        html_content=plan.html_content,
        frontmatter=plan.frontmatter,
        is_public=plan.is_public,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )
