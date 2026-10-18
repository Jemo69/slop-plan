import difflib
import re
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from tortoise.functions import Length
from typing import Optional, List
from db import User, Project, Plan, PlanPin, PlanVersion
from routes.auth import get_current_user
from services import versioning

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
    is_archived: bool = False
    is_pinned: bool = False
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
        is_archived=p.is_archived,
        is_pinned=is_pinned,
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


class PlanSummaryResponse(BaseModel):
    """A plan without its HTML body.

    List and search endpoints return this instead of PlanResponse, so a client can
    list or search an entire account without downloading every document. Opening a plan
    only needs the slug, because plans are served as pages at /p/{slug}.
    """

    id: str
    project_id: str
    title: str
    slug: str
    url: str
    description: str = ""
    is_public: bool
    is_archived: bool
    is_pinned: bool = False
    created_at: str
    updated_at: str
    size_bytes: int = 0


class PlanSearchResponse(BaseModel):
    plans: List[PlanSummaryResponse]
    # Number of matches before `limit` was applied, so a client can tell "that was
    # everything" from "there is more than you asked for".
    total: int
    query: str = ""


def _summary(row: dict, pinned_ids: set) -> PlanSummaryResponse:
    plan_id = str(row.get("id") or "")
    slug = row.get("slug") or ""
    frontmatter = row.get("frontmatter")
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    created_at = row.get("created_at")
    updated_at = row.get("updated_at")
    return PlanSummaryResponse(
        id=plan_id,
        project_id=str(row.get("project_id") or ""),
        title=row.get("title") or "",
        slug=slug,
        url=f"/p/{slug}",
        description=frontmatter.get("description") or "",
        is_public=bool(row.get("is_public")),
        is_archived=bool(row.get("is_archived")),
        is_pinned=plan_id in pinned_ids,
        created_at=created_at.isoformat() if created_at else "",
        updated_at=updated_at.isoformat() if updated_at else "",
        size_bytes=int(row.get("size_bytes") or 0),
    )


def _matches_summary(row: dict, terms: List[str]) -> bool:
    frontmatter = row.get("frontmatter")
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    haystack = " ".join(
        filter(
            None,
            [
                row.get("title") or "",
                row.get("slug") or "",
                frontmatter.get("description") or "",
            ],
        )
    ).lower()
    return all(term in haystack for term in terms)


# Declared before /{plan_id} on purpose. FastAPI matches routes in declaration order, so
# a later route would let the literal path "search" be captured as a plan_id and
# rejected as an invalid UUID.
@router.get("/search", response_model=PlanSearchResponse)
async def search_plans(
    q: Optional[str] = Query(None, description="Free-text search over title, slug and description"),
    project_id: Optional[str] = Query(None, description="Restrict to one project"),
    include_archived: bool = Query(False, description="Include archived plans"),
    limit: int = Query(50, description="Maximum number of plans to return (clamped to 1..200)"),
    user: User = Depends(get_current_user),
):
    """Search the caller's plans by title, slug or description.

    Returns metadata only - `html_content` is never serialised here, so searching an
    account costs a few hundred bytes per plan instead of a full document.
    """
    limit = max(1, min(200, limit))
    user_project_ids = await Project.filter(user_id=user.id).values_list("id", flat=True)
    query = Plan.filter(project_id__in=list(user_project_ids))
    if project_id:
        query = query.filter(project_id=project_id)
    if not include_archived:
        query = query.filter(is_archived=False)

    # LENGTH() in SQL rather than reading the column, so the documents never enter
    # memory. Both SQLite and libSQL speak it. The field is named as a string, which
    # Tortoise renders as the quoted column LENGTH("html_content") - it does not bind
    # it as a parameter, and Tortoise models expose no columns as class attributes.
    rows = await query.annotate(
        size_bytes=Length("html_content")
    ).values(
        "id",
        "project_id",
        "title",
        "slug",
        "frontmatter",
        "is_public",
        "is_archived",
        "created_at",
        "updated_at",
        "size_bytes",
    )

    # Normalised to str on both sides: the ORM hands back UUID objects for these
    # columns, so comparing raw values would never match.
    pinned_ids = {
        str(pinned_id)
        for pinned_id in await PlanPin.filter(user_id=user.id).values_list("plan_id", flat=True)
    }

    terms = [t for t in (q or "").lower().split() if t]
    if terms:
        rows = [row for row in rows if _matches_summary(row, terms)]

    # Python's sort is stable, so sorting least-significant key first yields
    # pinned-first, then most-recently-updated, then alphabetical by title.
    rows.sort(key=lambda r: (r.get("title") or "").lower())
    rows.sort(key=lambda r: r.get("updated_at") or r.get("created_at"), reverse=True)
    rows.sort(key=lambda r: str(r.get("id") or "") not in pinned_ids)

    return PlanSearchResponse(
        plans=[_summary(row, pinned_ids) for row in rows[:limit]],
        total=len(rows),
        query=q or "",
    )


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

    # Snapshot the pre-update content before mutating it. Only the fields a
    # version actually stores count: toggling publish/archive is state, not
    # content, so it should not litter the history.
    content_changing = any(
        field is not None and getattr(plan, field) != value
        for field, value in (
            ("title", request.title),
            ("html_content", request.html_content),
            ("frontmatter", request.frontmatter),
        )
    )
    if content_changing:
        await versioning.record_version(plan)

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


class VersionMeta(BaseModel):
    """History entry without the (potentially large) HTML body."""

    version: int
    title: str
    note: Optional[str] = None
    created_at: str
    size_bytes: int


class VersionListResponse(BaseModel):
    versions: List[VersionMeta]
    versioning_available: bool = True


class VersionDetail(VersionMeta):
    html_content: str
    frontmatter: Optional[dict] = None


class SnapshotRequest(BaseModel):
    note: Optional[str] = None


def _version_meta(v: PlanVersion) -> VersionMeta:
    return VersionMeta(
        version=v.version,
        title=v.title,
        note=v.note,
        created_at=v.created_at.isoformat() if v.created_at else "",
        size_bytes=len(v.html_content or ""),
    )


@router.get("/{plan_id}/versions", response_model=VersionListResponse)
async def list_versions(
    plan_id: str,
    user: User = Depends(get_current_user),
):
    """Version history for a plan, newest first."""
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        versions = (
            await PlanVersion.filter(plan_id=plan.id).order_by("-version").all()
        )
    except Exception:  # noqa: BLE001
        # Degrade to empty history rather than failing the request, so a
        # deployment without the table stays usable.
        return VersionListResponse(versions=[], versioning_available=False)

    return VersionListResponse(versions=[_version_meta(v) for v in versions])


@router.get("/{plan_id}/versions/{version}", response_model=VersionDetail)
async def get_version(
    plan_id: str,
    version: int,
    user: User = Depends(get_current_user),
):
    """Full content of one stored version."""
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        stored = await PlanVersion.filter(plan_id=plan.id, version=version).first()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Version not found")

    if not stored:
        raise HTTPException(status_code=404, detail="Version not found")

    return VersionDetail(
        **_version_meta(stored).model_dump(),
        html_content=stored.html_content,
        frontmatter=stored.frontmatter,
    )


@router.post("/{plan_id}/versions", response_model=VersionDetail, status_code=201)
async def create_snapshot(
    plan_id: str,
    request: SnapshotRequest = SnapshotRequest(),
    user: User = Depends(get_current_user),
):
    """Manually snapshot the plan's current content, with an optional note."""
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    number = await versioning.record_version(plan, note=request.note)
    if number is None:
        raise HTTPException(status_code=503, detail="Version history is unavailable")

    stored = await PlanVersion.filter(plan_id=plan.id, version=number).first()
    return VersionDetail(
        **_version_meta(stored).model_dump(),
        html_content=stored.html_content,
        frontmatter=stored.frontmatter,
    )


@router.post("/{plan_id}/versions/{version}/restore", response_model=PlanResponse)
async def restore_version(
    plan_id: str,
    version: int,
    user: User = Depends(get_current_user),
):
    """Roll a plan back to a previous version.

    The current content is snapshotted first, so a restore is itself
    reversible through this same endpoint.
    """
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    ok = await versioning.restore_version(plan, version)
    if not ok:
        raise HTTPException(status_code=404, detail="Version not found")

    return to_response(plan)


@router.get("/{plan_id}/diff", response_model=dict)
async def diff_versions(
    plan_id: str,
    from_version: Optional[int] = Query(None, alias="from"),
    to_version: Optional[int] = Query(None, alias="to"),
    context: int = Query(3, ge=0, le=20),
    user: User = Depends(get_current_user),
):
    """Unified diff of two versions, or of a version against the live plan.

    Standard library only, so the deploy footprint is unchanged.
    """
    try:
        uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan_id format")

    plan = await _get_user_plan(plan_id, user)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    async def _resolve(number: Optional[int]) -> str:
        if number is None:
            return plan.html_content or ""
        stored = await PlanVersion.filter(plan_id=plan.id, version=number).first()
        if not stored:
            raise HTTPException(status_code=404, detail=f"Version {number} not found")
        return stored.html_content or ""

    before = await _resolve(from_version)
    after = await _resolve(to_version)

    diff_lines = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"v{from_version}" if from_version else "current",
            tofile=f"v{to_version}" if to_version else "current",
            lineterm="",
            n=context,
        )
    )

    added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )

    return {
        "from_version": from_version,
        "to_version": to_version,
        "added": added,
        "removed": removed,
        "changed": bool(diff_lines),
        "diff": "\n".join(diff_lines),
    }
