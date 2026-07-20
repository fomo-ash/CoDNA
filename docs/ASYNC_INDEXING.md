# Asynchronous Repository Indexing

> **Status:** Current implementation
> **Last reviewed:** 2026-07-20

## Purpose

Indexing moves repository content into durable, owner-scoped evidence without blocking the API request that starts it. The API creates a job and queues a Celery task through Redis; the worker performs repository work and writes results to PostgreSQL.

```text
POST /repositories/{id}/index
  ↓
Durable job + Redis/Celery enqueue
  ↓
Shallow clone
  ↓
Inventory and change detection
  ↓
Parse → knowledge → chunks → relationship edges
  ↓
History refresh
  ↓
Job complete
  ↓
Optional separate embedding task
```

The `POST /api/v1/repositories/{repository_id}/index` endpoint returns `202 Accepted` with `repository_id`, `job_id`, and `status`. If an active index job already exists for that repository, it is reused rather than duplicated.

## Stages

### Clone and inventory

The worker shallow-clones the repository into `REPOSITORY_WORKSPACE_PATH`. Private clones use the backend-stored GitHub token only when needed; the token is never included in API responses.

Discovery stores safe inventory metadata—path, filename, extension, language hint, byte size, SHA-256 hash, and binary flag—in `repository_files`, and stores aggregate counts in `repository_statistics`. It skips VCS/dependency/build/editor folders, secret-like environment files, symlinks, known binary assets, and files above `REPOSITORY_FILE_MAX_BYTES` (10 MiB by default).

### Incremental analysis

The worker compares the discovered inventory with persisted hashes. For changed paths, it:

1. parses supported files in an isolated subprocess with Tree-sitter;
2. replaces parse results and extracted knowledge for the changed files;
3. rebuilds chunks for changed paths and known relationship dependents; and
4. persists repository-local relationship edges.

Unchanged files retain their existing parse, knowledge, and chunk records. Removed files are removed through inventory synchronization. Supported parsers are Python, JavaScript, JSX, TypeScript, and TSX; unsupported text and binary files retain auditable parse statuses.

### History and embeddings

The worker refreshes accessible GitHub history artifacts after repository analysis. A history failure is logged and does not invalidate a successful code index.

When an embedding provider is configured and indexed content changed, the worker queues a separate embedding task. That task stores chunk vectors in pgvector and updates embedding state on the repository. The index stays browseable and lexically searchable if embedding generation is unavailable or fails.

## Completion and failure

Successful jobs move through `queued → running → completed`; the repository becomes `ready`. On an unhandled worker failure, the job stores a safe error summary and the repository becomes `failed`.

Use `GET /api/v1/jobs/{job_id}` to read job state. Use the repository explorer to browse the resulting files, parse records, knowledge facts, chunks, history, retrieval results, graph evidence, and cited answers.

## Operational notes

```bash
# Apply migrations, then start the local stack.
docker compose run --rm migrate
API_PORT=8001 WEB_PORT=3333 NEXT_PUBLIC_API_URL=http://localhost:8001 docker compose up -d --build

# Inspect worker activity.
docker compose logs -f worker
```

For endpoint contracts see [API.md](API.md); for the full system boundaries see [ARCHITECTURE.md](ARCHITECTURE.md).
