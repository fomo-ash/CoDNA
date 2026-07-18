# Repository Inventory and File Discovery

## Purpose

This milestone extends repository indexing after cloning. The worker now discovers repository files, stores file inventory metadata, stores aggregate repository statistics, and only then marks the repository `ready`.

This stage does not implement Tree-sitter, AST extraction, semantic chunks, embeddings, pgvector, knowledge graph data, AI summaries, or chat.

## Runtime Flow

```text
User imports repository
        |
        v
POST /api/v1/repositories/{repository_id}/index
        |
        v
Create job and enqueue Celery task
        |
        v
Worker clones repository
        |
        v
Worker discovers file inventory
        |
        v
Persist repository_files
        |
        v
Persist repository_statistics
        |
        v
Job completed and repository ready
```

## Modules

`app/modules/files/discovery.py`

Filesystem-only discovery. It walks the cloned repository, applies centralized ignore rules, detects extension and language, computes file size and SHA-256 hash, and marks binary files. It contains no database code so future parser stages can reuse the same discovery result.

`app/modules/files/service.py`

Database boundary for inventory. It validates repository ownership, replaces discovered files after a scan, persists statistics, lists files with pagination and filters, and reads persisted stats.

`app/modules/files/router.py`

Authenticated HTTP API for file inventory and stats. It exposes:

- `GET /api/v1/repositories/{repository_id}/files`
- `GET /api/v1/repositories/{repository_id}/stats`

`app/modules/files/schemas.py`

Response schemas for file rows and repository statistics.

`app/modules/files/interfaces.py`

Protocol boundary used by routes and tests.

## Database Changes

Migration:

```text
apps/api/alembic/versions/20260718_000008_create_repository_files_table.py
```

New table: `repository_files`

Stores one row per discovered file:

- `id`
- `repository_id`
- `path`
- `filename`
- `extension`
- `language`
- `size_bytes`
- `sha256`
- `is_binary`
- `discovered_at`
- `created_at`
- `updated_at`

Indexes:

- `repository_id`
- `(repository_id, path)`
- `(repository_id, language)`

New table: `repository_statistics`

Stores persisted aggregate scan results:

- `repository_id`
- `total_files`
- `source_files`
- `binary_files`
- `total_size_bytes`
- `detected_languages`
- `last_scan_at`

Statistics are persisted rather than recomputed on every request.

## Ignore Rules

Discovery skips noisy or unsafe directories:

```text
.git/
.github/
node_modules/
dist/
build/
.next/
coverage/
__pycache__/
venv/
.venv/
.idea/
.vscode/
target/
vendor/
```

Discovery skips known binary asset extensions:

```text
*.png
*.jpg
*.jpeg
*.gif
*.ico
*.pdf
*.zip
*.tar
*.gz
*.jar
*.exe
*.dll
```

Files larger than 10 MB are skipped.

Other binary files, such as `.mp3`, `.mpeg`, or `.ttf`, are currently inventoried with `is_binary=true`. They count toward `total_files` and `binary_files`, but not `source_files`.

Text files with no language mapping, such as `.gitignore` or `.svg`, count toward `total_files` but not `source_files`.

## API Verification

After indexing a repository, list discovered files:

```bash
curl "http://localhost:8001/api/v1/repositories/{repository_id}/files?page=1&page_size=100" \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

Expected response shape:

```json
{
  "files": [
    {
      "path": "src/App.jsx",
      "filename": "App.jsx",
      "extension": "jsx",
      "language": "JavaScript",
      "size_bytes": 2925,
      "sha256": "26240b0c8bf6bbdf899f8903b47bb2e03bc04f325abb53f08086bc23dfdf6ce9",
      "is_binary": false
    }
  ],
  "page": 1,
  "page_size": 100,
  "has_next_page": false
}
```

Read persisted stats:

```bash
curl "http://localhost:8001/api/v1/repositories/{repository_id}/stats" \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

Expected response shape:

```json
{
  "repository_id": "2353ab83-0db6-49e4-8503-83fd1fc0bfef",
  "total_files": 39,
  "source_files": 33,
  "binary_files": 3,
  "total_size_bytes": 7657956,
  "languages": {
    "CSS": 3,
    "HTML": 1,
    "JSON": 2,
    "Markdown": 1,
    "JavaScript": 26
  },
  "last_scan_at": "2026-07-18T08:41:48.659634Z"
}
```

## Local Test Verification

From the repository root:

```bash
source .venv/bin/activate
python -m pytest apps/api/tests/test_repository_file_discovery.py -q
```

Expected:

```text
11 passed
```

The root `pytest.ini` sets:

```ini
[pytest]
pythonpath = apps/api
```

This lets tests import the backend package as `app`.

## Docker Verification

Run Postgres and Redis:

```bash
docker compose up -d postgres redis
```

Apply migrations inside Docker:

```bash
docker compose run --rm migrate
```

Start API and worker:

```bash
API_PORT=8001 docker compose up api worker
```

If port `8000` is free and you want the default port:

```bash
docker compose up api worker
```

## Troubleshooting Notes

### `ModuleNotFoundError: No module named 'app'`

Cause: pytest was run from the repo root without adding `apps/api` to `PYTHONPATH`.

Fix: keep `pytest.ini` committed:

```ini
[pytest]
pythonpath = apps/api
```

### `repository_workspace_path Field required`

Cause: importing the worker loads Celery settings. Older local `.env` files did not define `REPOSITORY_WORKSPACE_PATH`.

Fix: `Settings` now has a safe local default:

```text
/tmp/codna/repositories
```

Docker still overrides this with:

```text
/var/lib/codna/repositories
```

### `Temporary failure in name resolution` for host `postgres`

Cause: running `alembic upgrade head` from the WSL host while `DATABASE_URL` points to Docker's internal host name:

```text
postgresql+asyncpg://postgres:postgres@postgres:5432/codna
```

The host name `postgres` resolves inside Docker containers, not from the host shell.

Fix: run migrations inside Docker:

```bash
docker compose run --rm migrate
```

### `Bind for 0.0.0.0:8000 failed: port is already allocated`

Cause: another process or container is already using host port `8000`.

Fix: run the API on another host port:

```bash
API_PORT=8001 docker compose up api worker
```

### `relation "repository_files" does not exist`

Cause: API route was working, but the inventory migration had not been applied.

Fix:

```bash
docker compose run --rm migrate
```

If Alembic does not apply `20260718_000008`, verify the migration exists inside the image:

```bash
docker compose run --rm migrate ls -la alembic/versions
```

If the file is missing, rebuild without cache:

```bash
docker compose build --no-cache api migrate
docker compose run --rm migrate alembic upgrade head
```

Confirm database state:

```bash
docker compose exec -T postgres psql -U postgres -d codna \
  -c "select version_num from alembic_version;" \
  -c "\dt"
```

Expected:

```text
20260718_000008
repository_files
repository_statistics
```

## What To Push

Push the implementation and the tests together. The tests are part of the milestone because they define and protect the inventory contract.

Include:

- `pytest.ini`
- `apps/api/app/modules/files/`
- `apps/api/app/db/models/repository_file.py`
- `apps/api/app/db/models/repository_statistics.py`
- `apps/api/alembic/versions/20260718_000008_create_repository_files_table.py`
- `apps/api/tests/test_repository_file_discovery.py`
- worker/config/router/model wiring changes
- `docs/API.md`
- `docs/ASYNC_INDEXING.md`
- `docs/REPOSITORY_INVENTORY.md`

Do not push local secrets:

- `.env`
- `apps/api/.env`

If a GitHub client secret was exposed in terminal output, rotate it before sharing logs or pushing to any remote.

## Next Backend Milestone

The next milestone should be Tree-sitter parsing.

Recommended scope:

1. Consume rows from `repository_files`.
2. Parse only `is_binary=false` files with supported languages.
3. Store parse status per file.
4. Extract AST/symbol metadata.
5. Do not create embeddings, summaries, graph edges, or AI responses yet.

The inventory layer implemented here is the canonical input for that parser stage.
