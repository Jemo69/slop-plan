# HTML Plan Service Backend

A FastAPI backend for storing and serving HTML plans with Turso/libSQL support.

## Features

- User authentication with API keys
- Project management (CRUD)
- Plan management (CRUD)
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
- `GET /api/plans` - List user's plans
- `POST /api/plans` - Create plan
- `GET /api/plans/{id}` - Get plan
- `PUT /api/plans/{id}` - Update plan
- `DELETE /api/plans/{id}` - Delete plan
- `POST /api/plans/{id}/publish` - Make plan public
- `POST /api/plans/{id}/unpublish` - Make plan private

### Public Plans
- `GET /p/{slug}` - Serve public plan HTML

## Database

Uses Tortoise ORM with SQLite (dev) or Turso/libSQL (production).

Run migrations:
```bash
tortoise init
tortoise makemigrations
tortoise migrate
```
