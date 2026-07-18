# Repository Indexing Pipeline

## Purpose

This document describes the current repository indexing pipeline.

Indexing is asynchronous. The API creates a durable job, publishes work to Redis, and returns immediately. A Celery worker then clones the repository, discovers files, parses supported source files, extracts structured repository knowledge, builds semantic chunks, and persists the results for later embeddings, search, and AI features.

This milestone intentionally stops before embeddings, vector search, graph generation, and AI orchestration.

Related API reference: [API.md](API.md).

## Current Flow

```text
Authenticated client
  -> POST /api/v1/repositories/{repository_id}/index
  -> create or reuse active repository_index job
  -> publish Celery task to Redis
  -> worker clones repository
  -> worker discovers file inventory
  -> worker parses supported source files with Tree-sitter
  -> worker extracts structured knowledge
  -> worker builds semantic chunks from persisted knowledge and stored file ranges
  -> worker persists inventory, parse results, knowledge items, and chunks
  -> worker marks job completed and repository ready
```

PostgreSQL is the source of truth. Redis only transports queued work.

## Pipeline Stages

### 1. Repository Clone

The worker shallow-clones the repository into `REPOSITORY_WORKSPACE_PATH`.

Private repository cloning uses the backend-stored GitHub access token from OAuth. The token is not exposed through API responses.

### 2. Repository Inventory

The worker discovers repository files and stores safe metadata:

- path
- filename
- extension
- language hint
- size
- SHA-256 hash
- binary flag

Discovery skips noisy or unsafe paths such as VCS folders, dependency folders, build output, secret-like env files, symlinks, and files above `REPOSITORY_FILE_MAX_BYTES`.

### 3. Source Parsing

Supported source files are parsed with Tree-sitter.

Current parser support:

| Extension | Parser |
| --- | --- |
| `.py` | Python |
| `.js` | JavaScript |
| `.jsx` | JavaScript |
| `.ts` | TypeScript |
| `.tsx` | TSX |

Parse results are stored for every inventoried file:

| Status | Meaning |
| --- | --- |
| `parsed` | Supported file parsed with no Tree-sitter syntax errors. |
| `syntax_error` | Supported file parsed, but Tree-sitter reported syntax errors. |
| `unsupported` | Text file exists, but no parser is configured yet. |
| `skipped` | Binary file or intentionally skipped file. |
| `failed` | Parser failed unexpectedly. |

The parser extracts source-level metadata including source file summaries, imports, symbols, symbol kind, signatures, and start/end lines.

Parser execution is isolated in a subprocess from the worker's async database process. This keeps native parser failures from corrupting the long-running Celery worker process.

### 4. Knowledge Extraction

Knowledge extraction runs after inventory and parsing. Extractors are separate modules behind a common interface so new extractors can be added without rewriting the indexing task.

Current extractors:

| Source type | Extractor | Item types |
| --- | --- | --- |
| `source_code` | Tree-sitter parse result extractor | `source_file`, `symbol`, `import` |
| `documentation` | Markdown extractor | `document`, `document_section` |
| `database_schema` | Prisma schema extractor | `prisma_schema`, `prisma_model`, `prisma_enum` |
| `configuration` | Project config extractor | `package_manifest`, `python_project`, `python_requirements`, `typescript_config`, `dockerfile`, `compose_config` |

Markdown extraction captures titles, headings, sections, links, code blocks, and front matter metadata.

Prisma extraction captures models, fields, relations, enums, indexes, and constraints.

Configuration extraction captures dependencies, scripts, package manager signals, frameworks, runtime hints, build commands, Docker commands, Compose services, Python project metadata, and requirements.

### 5. Semantic Chunk Building

Chunk building runs after knowledge persistence. It consumes `repository_knowledge_items` and uses the stored path and line metadata to slice the cloned file content. It never invokes Tree-sitter or any other parser.

Current chunk types:

| Source type | Chunk types |
| --- | --- |
| `source_code` | `class`, `function`, `source_file` for small symbol-free files |
| `documentation` | `documentation_section` |
| `database_schema` | `prisma_model` |
| `configuration` | `configuration` |

Class chunks include their imports, used imports, constructor, methods, fields, decorators, inheritance, and implemented interfaces. Function chunks include signatures, parameters, return types, decorators, visibility, local variables, calls, references, and used imports. Source symbols have stable IDs such as `environment.py::StudentLifeEnv::step`.

Each chunk also has deterministic repository-aware metadata: its module, repository-relative path, source range, language, stable ID, and a `relationships` object. The builder resolves repository-local imports, calls, references, `called_by`, and `imported_by` links when they are unambiguous. Unresolved relationship categories remain empty lists.

Source chunks expose `file_imports` for the complete file import set and `used_imports` for the imports referenced by that specific function, class, constants group, or types group. Legacy `imports` remains on file-level chunks only. The parser also records explicit exports (including Python `__all__` when statically declared), so downstream graph work does not need to parse source again.

Markdown section chunks record outbound links, code blocks, table/image presence, and section depth. Configuration chunks additionally identify framework, runtime, package manager, build tool, testing framework, linting tools, and formatter when those signals are present in the extracted manifest data.

## Key Endpoints

### Start indexing

```http
POST /api/v1/repositories/{repository_id}/index
Authorization: Bearer <codedna-jwt>
```

Response:

```json
{
  "repository_id": "repository-uuid",
  "job_id": "job-uuid",
  "status": "queued"
}
```

If a queued or running index job already exists for that repository, the API returns the existing active job instead of enqueueing duplicate work.

### Read job status

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <codedna-jwt>
```

Expected successful sequence:

```text
queued -> running -> completed
```

On success, the linked repository ends as `ready`.

### List inventory

```http
GET /api/v1/repositories/{repository_id}/files?page=1&page_size=100
Authorization: Bearer <codedna-jwt>
```

### List parse results

```http
GET /api/v1/repositories/{repository_id}/parse-results?page=1&page_size=100
Authorization: Bearer <codedna-jwt>
```

Useful filters:

```http
GET /api/v1/repositories/{repository_id}/parse-results?status=failed
GET /api/v1/repositories/{repository_id}/parse-results?status=syntax_error
GET /api/v1/repositories/{repository_id}/parse-results?language=Python
```

### List knowledge items

```http
GET /api/v1/repositories/{repository_id}/knowledge?page=1&page_size=100
Authorization: Bearer <codedna-jwt>
```

Useful filters:

```http
GET /api/v1/repositories/{repository_id}/knowledge?source_type=source_code
GET /api/v1/repositories/{repository_id}/knowledge?source_type=documentation
GET /api/v1/repositories/{repository_id}/knowledge?source_type=database_schema
GET /api/v1/repositories/{repository_id}/knowledge?source_type=configuration
GET /api/v1/repositories/{repository_id}/knowledge?item_type=symbol
GET /api/v1/repositories/{repository_id}/knowledge?path_prefix=src/
```

### List semantic chunks

```http
GET /api/v1/repositories/{repository_id}/chunks?page=1&page_size=100
Authorization: Bearer <codedna-jwt>
```

Useful filters:

```http
GET /api/v1/repositories/{repository_id}/chunks?source_type=source_code
GET /api/v1/repositories/{repository_id}/chunks?chunk_type=class
GET /api/v1/repositories/{repository_id}/chunks?chunk_type=documentation_section
```

### Read one chunk

```http
GET /api/v1/chunks/{chunk_id}
Authorization: Bearer <codedna-jwt>
```

## Docker Verification

Build images after backend code changes:

```bash
docker compose build api worker migrate
```

Start dependencies:

```bash
docker compose up -d postgres redis
```

Apply migrations:

```bash
docker compose run --rm migrate
```

Start API and worker. If local port `8000` is already in use, publish the API on `8001`:

```bash
API_PORT=8001 docker compose up -d api worker
```

Check services:

```bash
docker compose ps
docker compose logs --tail=100 worker
```

Check API health:

```bash
curl -i http://localhost:8001/api/v1/health
```

If the API is healthy inside Docker but host curl fails immediately, wait a few seconds and retry. WSL/Windows port forwarding can lag briefly after container recreation.

## Manual 2-3 Repository Test

Set the API URL and token:

```bash
export API=http://localhost:8001/api/v1
export TOKEN="paste-codedna-jwt-here"
```

For each test repository:

```bash
curl -s -X POST "$API/repositories" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"OWNER/REPO"}'
```

Copy the returned repository `id`, then start indexing:

```bash
curl -s -X POST "$API/repositories/REPOSITORY_ID/index" \
  -H "Authorization: Bearer $TOKEN"
```

Copy the returned `job_id`, then poll:

```bash
curl -s "$API/jobs/JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
```

After `status` becomes `completed`, verify the outputs:

```bash
curl -s "$API/repositories/REPOSITORY_ID/files?page_size=20" \
  -H "Authorization: Bearer $TOKEN"

curl -s "$API/repositories/REPOSITORY_ID/parse-results?page_size=20" \
  -H "Authorization: Bearer $TOKEN"

curl -s "$API/repositories/REPOSITORY_ID/knowledge?page_size=20" \
  -H "Authorization: Bearer $TOKEN"

curl -s "$API/repositories/REPOSITORY_ID/chunks?page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Recommended coverage:

- One Python repository.
- One JavaScript/TypeScript frontend repository.
- One repository with docs and project configuration, such as `README.md`, `package.json`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, or `prisma/schema.prisma`.

Expected result:

- Repository status is `ready`.
- Job status is `completed`.
- Inventory rows exist.
- Parse rows exist for all inventoried files.
- Knowledge items exist for source code and any available docs/schema/config files.
- Semantic chunks exist for source code and any available docs/schema/config files.
- Unsupported files are expected for formats without a parser, such as CSS, SVG, HTML, lockfiles, media, fonts, and some config files.

## Troubleshooting

### Migration appears stuck

Check whether the migration already applied:

```bash
docker compose exec -T postgres psql -U postgres -d codna -c "select * from alembic_version;"
```

The current semantic chunk milestone expects:

```text
20260718_000011
```

Also confirm the new tables exist:

```bash
docker compose exec -T postgres psql -U postgres -d codna -c "select table_name from information_schema.tables where table_schema='public' and table_name in ('repository_file_parses','repository_knowledge_items','repository_chunks') order by table_name;"
```

If the DB is already at the latest revision and the one-off migrate container is still running with no new logs, stop only that one-off container and continue.

### API port is already allocated

Use another host port:

```bash
API_PORT=8001 docker compose up -d api worker
```

Then use:

```bash
export API=http://localhost:8001/api/v1
```

### Worker fails or a job stays running

Check worker logs:

```bash
docker compose logs --tail=200 worker
```

Check persisted job and repository state:

```bash
docker compose exec -T postgres psql -U postgres -d codna -c "select id, repository_id, status, error_message, started_at, completed_at from jobs order by created_at desc limit 10;"
```

If a worker process crashes, the job can remain `running` because the process died before the failure handler wrote state. The worker logs are the source for diagnosing that case.

### Parsing crashes

Parser work runs in a subprocess. A parser subprocess failure should now fail the job with a controlled error instead of crashing the Celery worker process.

The worker uses byte offsets to compute source line numbers and serializes parse results through plain JSON before database persistence.

## Current Acceptance Criteria

This milestone is complete when:

- Authenticated users can import repositories.
- Authenticated repository owners can enqueue indexing jobs.
- Duplicate active index requests return the existing active job.
- Worker clones the repository into its controlled workspace.
- Worker persists repository inventory and statistics.
- Worker persists parse rows for discovered files.
- Worker extracts source code, documentation, database schema, and configuration knowledge.
- Worker builds semantic chunks from persisted knowledge without rerunning Tree-sitter.
- Job status moves to `completed` on success and repository status moves to `ready`.
- Failed worker execution records a safe error summary and repository status moves to `failed`.
- Inventory, parse result, knowledge, and chunk endpoints are owner-scoped.
- Focused backend tests pass.

## Next Milestones

Do next:

1. Add embeddings for chunks and store vectors in PostgreSQL/pgvector.
2. Add retrieval APIs over chunks and metadata filters.
3. Add AI answer orchestration using retrieved chunks as context.
4. Add graph generation after stable entities and relationships are available.

Do not skip straight to AI orchestration. The retrieval layer needs stable chunks and metadata first.
