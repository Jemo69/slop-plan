"""Version history for plans.

Design note (deployment safety)
-------------------------------
Vercel never runs migrations for this service: ``vercel.json`` has no
build command, aerich was removed because it crashed cold starts, and
``RegisterTortoise`` is used without ``generate_schemas`` (it defaults to
False). The production Turso schema is therefore applied by hand.

That means a freshly deployed build can legitimately be running against a
database that has no ``plan_versions`` table. If any code path assumed the
table exists, every ``PUT /api/plans/{id}`` would start returning 500 in
production the moment the change reached master.

So this module treats versioning as strictly additive and fail-soft:

1. :func:`ensure_version_schema` creates the table idempotently on startup,
   wrapped so it can never break a cold start.
2. Every other helper swallows storage errors and reports "unavailable"
   instead of raising, so plan CRUD keeps working exactly as before.

History is best-effort until the table exists; it is never load-bearing.
"""

import inspect
import logging

from tortoise import connections
from tortoise.exceptions import OperationalError

logger = logging.getLogger(__name__)

TABLE = "plan_versions"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT NOT NULL,
    html_content TEXT NOT NULL,
    frontmatter JSON,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    UNIQUE(plan_id, version)
)
"""

# Substrings that mean "this deployment's database predates versioning".
_MISSING_TABLE_MARKERS = (
    "no such table",
    "does not exist",
    "undefined table",
)

# A concurrent writer claiming the same version number surfaces as a UNIQUE
# violation; anything else is not worth retrying.
_UNIQUE_MARKERS = ("unique", "duplicate")


def _is_missing_table(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _MISSING_TABLE_MARKERS)


def _is_version_collision(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _UNIQUE_MARKERS)


def _same_content(stored, plan) -> bool:
    """True when a stored version already matches the plan's live content."""
    return (
        stored.html_content == plan.html_content
        and stored.title == plan.title
        and (stored.frontmatter or None) == (plan.frontmatter or None)
    )


async def ensure_version_schema() -> bool:
    """Create the version table if missing. Never raises.

    Safe to call on every cold start: the statement is idempotent and any
    failure (permissions, network, a read-only replica) is logged and
    ignored, leaving versioning disabled rather than breaking the app.
    """
    try:
        connection = connections.get("default")
        result = connection.execute_query(CREATE_TABLE_SQL)
        if inspect.isawaitable(result):
            await result
        return True
    except Exception as exc:  # noqa: BLE001 - must never break startup
        logger.warning("versioning disabled: could not ensure %s (%s)", TABLE, exc)
        return False


async def _latest_version(plan) -> int:
    # Read via the ORM rather than raw SQL: this repo ships a custom libSQL
    # adapter whose raw-result shape differs from SQLite's, and the ORM
    # normalises both.
    from db import PlanVersion

    newest = (
        await PlanVersion.filter(plan_id=plan.id)
        .order_by("-version")
        .first()
    )
    return int(newest.version) if newest is not None else 0


async def record_version(plan, note: str = None) -> int | None:
    """Snapshot the plan's *current* content as its next version.

    Returns the new version number, or ``None`` when history is unavailable
    (table missing or a write failed). Callers treat ``None`` as "continue
    without history" -- it is never an error.

    With no ``note`` this is the automatic pre-update snapshot, so an
    unchanged plan is not re-recorded. Passing an explicit ``note`` always
    records, letting you label a deliberate snapshot of current content.
    """
    from db import PlanVersion  # local import: avoids import cycle at startup

    if note is None:
        try:
            newest = (
                await PlanVersion.filter(plan_id=plan.id)
                .order_by("-version")
                .first()
            )
        except Exception as exc:  # noqa: BLE001
            if _is_missing_table(exc):
                logger.warning("versioning disabled: %s is missing", TABLE)
            else:
                logger.warning("version history read failed: %s", exc)
            return None

        if newest is not None and _same_content(newest, plan):
            return newest.version

    next_version = await _latest_version(plan) + 1

    for _ in range(2):  # one retry covers a concurrent writer's number clash
        try:
            await PlanVersion.create(
                plan_id=plan.id,
                version=next_version,
                title=plan.title,
                html_content=plan.html_content,
                frontmatter=plan.frontmatter,
                note=note,
            )
            return next_version
        except Exception as exc:  # noqa: BLE001
            if _is_missing_table(exc):
                logger.warning("versioning disabled: %s is missing", TABLE)
                return None
            if not _is_version_collision(exc):
                logger.warning("version snapshot failed: %s", exc)
                return None
            next_version = await _latest_version(plan) + 1
            logger.info("version number clash, retrying as v%s", next_version)
    return None


async def restore_version(plan, version: int) -> bool:
    """Copy a stored version back onto the plan.

    The pre-restore state is snapshotted first, so a restore is itself
    reversible. Returns False when the version is missing or history is
    unavailable; the caller then leaves the plan untouched.
    """
    from db import PlanVersion

    try:
        stored = await PlanVersion.filter(plan_id=plan.id, version=version).first()
    except Exception as exc:  # noqa: BLE001
        if _is_missing_table(exc):
            logger.warning("versioning disabled: %s is missing", TABLE)
        else:
            logger.warning("version lookup failed: %s", exc)
        return False

    if stored is None:
        return False

    # Keep history reversible: preserve what we are about to overwrite.
    await record_version(plan, note=f"before restore to v{version}")

    plan.title = stored.title
    plan.html_content = stored.html_content
    plan.frontmatter = stored.frontmatter
    await plan.save()
    return True


def is_missing_table_error(exc: Exception) -> bool:
    """Exposed for tests and callers that need to detect a stale schema."""
    return _is_missing_table(exc)


__all__ = [
    "CREATE_TABLE_SQL",
    "TABLE",
    "OperationalError",
    "ensure_version_schema",
    "is_missing_table_error",
    "record_version",
    "restore_version",
]
