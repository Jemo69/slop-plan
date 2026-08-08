import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from db import User, Project, Plan, PlanPin, ProjectPin
from routes.auth import get_current_user

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    is_pinned: bool = False
    is_archived: bool = False
    created_at: str


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]


@router.get("", response_model=ProjectListResponse)
async def list_projects(user: User = Depends(get_current_user)):
    projects = await Project.filter(user_id=user.id, is_archived=False).all()

    pinned_project_ids = set(
        await ProjectPin.filter(user_id=user.id).values_list("project_id", flat=True)
    )

    project_responses = []
    for p in projects:
        project_responses.append(ProjectResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            is_pinned=p.id in pinned_project_ids,
            is_archived=p.is_archived,
            created_at=p.created_at.isoformat() if p.created_at else "",
        ))

    project_responses.sort(key=lambda r: (not r.is_pinned, r.created_at))

    return ProjectListResponse(projects=project_responses)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.create(
        user_id=user.id,
        name=request.name,
        description=request.description,
    )
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pin = await ProjectPin.filter(user_id=user.id, project_id=project.id).first()

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        is_pinned=pin is not None,
        is_archived=project.is_archived,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    plan_ids = await Plan.filter(project_id=project.id).values_list('id', flat=True)
    await PlanPin.filter(plan_id__in=list(plan_ids)).delete()
    await Plan.filter(project_id=project.id).delete()
    await ProjectPin.filter(user_id=user.id, project_id=project.id).delete()
    await project.delete()


@router.post("/{project_id}/pin", response_model=ProjectResponse, status_code=201)
async def pin_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = await ProjectPin.filter(user_id=user.id, project_id=project.id).first()
    if existing:
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_pinned=True,
            created_at=project.created_at.isoformat() if project.created_at else "",
        )

    await ProjectPin.create(user_id=user.id, project_id=project.id)

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        is_pinned=True,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )


@router.delete("/{project_id}/pin", status_code=204)
async def unpin_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await ProjectPin.filter(user_id=user.id, project_id=project.id).delete()


@router.post("/{project_id}/archive", response_model=ProjectResponse, status_code=200)
async def archive_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.is_archived:
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_archived=True,
            created_at=project.created_at.isoformat() if project.created_at else "",
        )

    project.is_archived = True
    await project.save()

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        is_archived=True,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )


@router.post("/{project_id}/unarchive", response_model=ProjectResponse, status_code=200)
async def unarchive_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = await Project.filter(id=project_id, user_id=user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.is_archived:
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            is_archived=False,
            created_at=project.created_at.isoformat() if project.created_at else "",
        )

    project.is_archived = False
    await project.save()

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        is_archived=False,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )
