# Agent Memory Service (Phases 0-2)

This repository implements:

- Phase 0: Baseline Foundation
- Phase 1: Identity and Auth Layer
- Phase 2: Policy Enforcement Layer

## Supabase mode

If `.env` contains:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

the API will use Supabase PostgREST for memory persistence automatically.

## Run migration

```powershell
python -m app.db.migrate
```

## Run PostgreSQL container + all migrations

```powershell
.\scripts\run_postgres_and_migrate.ps1
```

Optional flags:

```powershell
.\scripts\run_postgres_and_migrate.ps1 -Recreate -RunTests
```

## Run API server

```powershell
python -m app.server
```

## Run tests

```powershell
python -m pytest -q
```

## Docker VPS deployment

1. Create env file:

```powershell
Copy-Item .env.docker.example .env.docker
```

2. Fill required values in `.env.docker`:
- `AUTH_SECRET_CURRENT`
- Gateway auth vars for any agent you enable (`CLAUDE_*`, `AGENT_A_*`, `AGENT_B_*`)
- Optional `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`

3. Start API + central gateway:

```powershell
docker compose up -d --build
```

4. Verify health:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8787/health
```

The central gateway listens on `:8787` and forwards to the API container on `api:8000`.
