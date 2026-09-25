# HTML Plan Service Backend

A FastAPI backend for storing and serving HTML plans with Turso/libSQL support.

## Features

- User authentication with API keys
- Project management (CRUD)
- Plan management (CRUD)
- **Plan version history** — every update stores the previous content; restore and diff
- Pin plans to top of dashboard (per-user)
- Public plan serving via `/p/:slug`
- Open Graph and Twitter Card meta tags for social sharing
- Plan dashboard UI at `/dashboard`

## Setup

### Development

1. Install dependencies:
```bash
uv sync
```

2. Run the server:
```bash
uv run uvicorn main:app --reload
```

### Turso Production

1. Set environment variables:
```bash
export TURSO_DATABASE_URL="libsql://your-db.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
```

2. Update `tortoise_conf.py` to use Turso connection string.

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login to existing account

### Projects
- `GET /api/projects` - List user's projects
- `POST /api/projects` - Create project
- `GET /api/projects/{id}` - Get project
- `DELETE /api/projects/{id}` - Delete project

### Plans
- `GET /api/plans` - List user's plans (pinned plans returned first, includes `is_pinned` field)
- `POST /api/plans` - Create plan
- `GET /api/plans/{id}` - Get plan
- `PUT /api/plans/{id}` - Update plan
- `DELETE /api/plans/{id}` - Delete plan
- `POST /api/plans/{id}/publish` - Make plan public
- `POST /api/plans/{id}/unpublish` - Make plan private
- `POST /api/plans/{id}/pin` - Pin plan to top of dashboard
- `DELETE /api/plans/{id}/pin` - Unpin plan

### Plan Versions

Each update records the content it replaced, so the state before any change
is always recoverable. Versions are numbered per plan from 1.

- `GET /api/plans/{id}/versions` - List history (newest first, no HTML bodies)
- `GET /api/plans/{id}/versions/{n}` - Full content of one version
- `POST /api/plans/{id}/versions` - Manual snapshot (`{"note": "before redesign"}`)
- `POST /api/plans/{id}/versions/{n}/restore` - Roll back to version n
- `GET /api/plans/{id}/diff?from=1&to=2` - Unified diff (omit a side to diff against the live plan)

Notes:
- History covers `title`, `html_content` and `frontmatter`. Toggling
  publish/archive is state rather than content and does not create a version.
- A restore snapshots the current content first, so restores are reversible.
- History is private to the plan owner. Public `/p/:slug` links always serve
  the current version.

#### Deployment safety

This service does not run migrations on Vercel (`vercel.json` has no build
command and aerich was removed), so production schema changes are applied by
hand. The `plan_versions` table is therefore created idempotently on startup
by `services/versioning.ensure_version_schema()`, and every version write
degrades to a no-op if the table is unavailable. Plan create/update/delete
keep working either way; a missing table only disables history.

To apply the change through the migration files instead:

```bash
tortoise migrate
```

### Public Plans
- `GET /p/{slug}` - Serve public plan HTML

### Dashboard UI
- `GET /dashboard` - Plan dashboard (auth required)
- `GET /app` - Landing page

## Database

Uses Tortoise ORM with SQLite (dev) or Turso/libSQL (production).

Tables: `users`, `projects`, `plans`, `plan_pins`, `project_pins`, `plan_versions`

Run migrations:
```bash
tortoise init
tortoise makemigrations
tortoise migrate
```
