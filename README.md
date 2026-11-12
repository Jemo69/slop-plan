# slop-plan

Self-hosted HTML plan publishing (Slop Plans): FastAPI backend + dashboard + `plan` CLI.
Live app: https://slop-plans.vercel.app/dashboard

## Install the CLI

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/Jemo69/slop-plan/main/cli/install.sh | bash

# Or manually
cd cli && uv sync
```

Auth before any write operation:

```bash
plan auth init    # register — or: plan auth login
plan auth whoami  # verify session
```

Create and publish a plan:

```bash
plan projects create --name "My Project"
plan create --project <PROJECT_ID> --title "My Plan" --html plan.html
plan publish <PLAN_ID>   # private by default; publish only to share
```

Full command reference: [`cli/README.md`](cli/README.md).

## Run the server

```bash
cd backend && uv sync
export TURSO_DATABASE_URL="libsql://your-db.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
uv run uvicorn main:app --reload
```

Never commit `backend/.env` or `backend/local.db` — both are gitignored.
Backend details: [`backend/README.md`](backend/README.md).

## Layout

- `cli/` — `plan` CLI (`plan_cli/`, `install.sh`, `update-cli.sh`)
- `backend/` — FastAPI app (Turso/libSQL, dashboard templates, migrations)
- `api/` — serverless entry
