# HTML Plan Service Backend

A FastAPI backend for storing and serving HTML plans with Turso/libSQL support.

## Features

- User authentication with API keys
- Project management (CRUD)
- Plan management (CRUD)
- Pin plans to top of dashboard (per-user)
- Public plan serving via `/p/:slug`
- Open Graph and Twitter Card meta tags for social sharing

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
- `POST /api/plans/{id}/approve` - Approve plan
- `POST /api/plans/{id}/unapprove` - Unapprove plan
- `POST /api/plans/{id}/pin` - Pin plan to top of dashboard
- `DELETE /api/plans/{id}/pin` - Unpin plan

### Public Plans
- `GET /p/{slug}` - Serve public plan HTML

## Dashboard

Access the web dashboard at `/dashboard`. Features:

- View all plans grouped by project
- Pin/unpin plans (pinned plans appear at top)
- Approve/unapprove plans
- Preview plans in a modal
- Delete plans
- Browser notifications for new plans

## Database

Uses Tortoise ORM with SQLite (dev) or Turso/libSQL (production).

Tables: `users`, `projects`, `plans`, `plan_pins`

Run migrations:
```bash
tortoise init
tortoise makemigrations
tortoise migrate
```
