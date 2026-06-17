from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from models import User, Project
from routes.auth import get_current_user

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: str


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]


@router.get("", response_model=ProjectListResponse)
async def list_projects(user: User = Depends(get_current_user)):
    projects = await Project.filter(user=user).all()
    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                created_at=p.created_at.isoformat(),
            )
            for p in projects
        ]
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
):
    project = await Project.create(
        user=user,
        name=request.name,
        description=request.description,
    )
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.filter(id=project_id, user=user).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        created_at=project.created_at.isoformat(),
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
):
    project = await Project.filter(id=project_id, user=user).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await project.delete()
