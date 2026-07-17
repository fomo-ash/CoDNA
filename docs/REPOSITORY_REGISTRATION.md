# GitHub Repository Discovery and Import

## Overview

This milestone lets an authenticated user browse repositories accessible through GitHub OAuth and import one into CodeDNA. The backend fetches all repository metadata from GitHub; the frontend submits only a GitHub repository identifier.

The request flow is:

```text
Authenticated request
        |
        v
GitHub integration service
        |
        v
GitHub REST API
        |
        v
Repository persistence service
        |
        v
PostgreSQL repositories table
```

## What Changed

### API routes

The GitHub and repository routers are mounted under `/api/v1` and expose:

| Method | Endpoint | Purpose | Authentication |
| --- | --- | --- | --- |
| `GET` | `/api/v1/github/me` | Read the authenticated GitHub profile | Required |
| `GET` | `/api/v1/github/repositories` | Browse accessible GitHub repositories | Required |
| `POST` | `/api/v1/repositories` | Import one GitHub repository | Required |
| `GET` | `/api/v1/repositories` | List imported repositories owned by the current user | Required |
| `GET` | `/api/v1/repositories/{repository_id}` | Read one imported repository owned by the current user | Required |

### Ownership

The OAuth callback stores the GitHub access token on the backend `users` record. It is never returned to the frontend. `owner_id` is taken from the authenticated CodeDNA JWT and is not accepted from the request body.

The import request accepts exactly one of:

```json
{ "github_id": "12345" }
```

or:

```json
{ "full_name": "owner/repository" }
```

The backend fetches the canonical name, clone URL, default branch, visibility, and GitHub ID from GitHub before persisting them.

### Service and database layers

- `app/modules/github/client.py` encapsulates GitHub REST calls.
- `app/modules/github/service.py` handles GitHub token use, response transformation, and integration errors.
- `app/modules/github/router.py` exposes GitHub profile and repository discovery routes.
- `app/modules/github/schemas.py` defines GitHub-facing response models.
- `app/modules/repositories/router.py` coordinates import input and persistence.
- `app/modules/repositories/service.py` persists GitHub-canonical metadata asynchronously.
- `app/modules/repositories/schemas.py` rejects frontend metadata and validates import identifiers.
- `app/db/models/repository.py` defines the ORM mapping and status enum.
- `alembic/versions/20260717_000004_add_github_access_token.py` adds backend-only token storage.
- `alembic/versions/20260717_000005_update_repository_constraints.py` adds the status enum and owner-scoped uniqueness.

The `owner_id` column remains nullable for compatibility with the original foundation migration. New authenticated imports always populate it. PostgreSQL sets it to `NULL` if the owning user is deleted. Repository status is constrained to `registered`, `cloning`, `indexing`, `ready`, `failed`, or `archived`; only `registered` is used in this milestone.

### Docker and configuration

- The API Docker healthcheck probes `/api/v1/health`, matching the mounted router.
- `apps/api/.env` is injected into the local API container at runtime through Compose.
- `.env` files are excluded from Docker build context, so local secrets are not copied into images.

## Local Setup

Start the API and supporting services on port `8001`:

```bash
API_PORT=8001 docker compose up -d --build api postgres redis
```

Apply database migrations:

```bash
docker compose run --rm --build migrate
```

The local API base URL is:

```text
http://localhost:8001
```

If port `8000` is available, omit `API_PORT=8001` and use `http://localhost:8000` instead.

## Authentication Prerequisite

Repository routes require a CodeDNA JWT. Obtain one through the existing GitHub OAuth flow:

```bash
curl -sS http://localhost:8001/api/v1/auth/github/login
```

Open the returned `authorization_url` in a browser, approve the GitHub application, and copy the `access_token` returned by the callback. Keep the token local:

```bash
export CODEDNA_TOKEN='paste-the-token-locally'
```

Do not commit the token or place it in `.env.example`.

## Verification

### 1. Check service health

```bash
curl -i http://localhost:8001/api/v1/health
curl -i http://localhost:8001/api/v1/live
curl -i http://localhost:8001/api/v1/ready
```

Expected results are HTTP `200`. The readiness response should report both `database` and `redis` as `ok`.

Docker should also show the API as healthy:

```bash
docker compose ps
```

### 2. Confirm authentication protection

```bash
curl -i http://localhost:8001/api/v1/repositories
```

Expected response:

```json
{
  "detail": "Authentication required."
}
```

Expected status: `401 Unauthorized`.

### 3. Browse GitHub repositories

```bash
curl -i "http://localhost:8001/api/v1/github/repositories?visibility=all&sort=updated&page=1&per_page=30" \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

Expected status: `200 OK`. The response contains canonical GitHub repository metadata and a `has_next_page` flag.

### 4. Import a repository

```bash
curl -i -X POST http://localhost:8001/api/v1/repositories \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "example/example"
  }'
```

Expected status: `201 Created`. Save the returned `id` for the next check:

```bash
export REPOSITORY_ID='returned-uuid'
```

### 5. List and read imported repositories

```bash
curl -i http://localhost:8001/api/v1/repositories \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"

curl -i http://localhost:8001/api/v1/repositories/${REPOSITORY_ID} \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

Expected statuses: `200 OK`. The list response contains the newly registered repository, and the detail response contains the same `id` and `full_name`.

### 6. Verify duplicate handling

Repeat the import request with the same GitHub repository. Expected status: `409 Conflict`.

### 7. Verify migrations and database constraints

```bash
docker compose run --rm --build migrate alembic current
docker compose exec -T postgres psql -U postgres -d codna -c "\\d repositories"
```

The current Alembic revision should be `20260717_000005`. The `repositories` table should include:

- `ix_repositories_owner_id`
- `fk_repositories_owner_id_users`
- `uq_repositories_owner_github_id`
- `repository_status`

### 8. Run tests and source checks

```bash
PYTHONPATH=apps/api pytest apps/api/tests -q
docker compose run --rm --build api sh -c 'PYTHONPATH=/app pytest tests -q'
python3 -m compileall -q apps/api/app apps/api/alembic
git diff --check -- apps/api docker-compose.yml .dockerignore
```

## Expected Error Behavior

| Situation | Status |
| --- | --- |
| No JWT | `401 Unauthorized` |
| Invalid JWT or missing local user | `401 Unauthorized` |
| Invalid request fields | `422 Unprocessable Entity` |
| GitHub repository does not exist or is inaccessible | `404 Not Found` |
| GitHub API is unavailable | `502 Bad Gateway` |
| Same GitHub repository already imported by this user | `409 Conflict` |
| Repository does not belong to current user | `404 Not Found` |

## Current Scope

This milestone establishes the persistence and API boundary for GitHub repository discovery and import. It does not implement:

- Repository cloning
- Celery task scheduling
- Source parsing and indexing
- pgvector embeddings
- Relational knowledge graph tables
- AI orchestration
