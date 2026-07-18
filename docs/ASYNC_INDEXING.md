# Asynchronous Indexing Infrastructure

## Purpose

This document describes the asynchronous indexing infrastructure milestone after GitHub repository discovery and import.

The goal is to establish the asynchronous execution framework before adding parsing, embeddings, graph generation, or AI functionality.

This milestone is implemented as infrastructure only.
The worker task now performs a shallow Git clone into a controlled local workspace, updates repository and job status, and exits successfully.

## Target Flow

```text
Authenticated client
        |
        v
POST /api/v1/repositories/{repository_id}/index
        |
        v
Create Job record with status=queued
        |
        v
Publish Celery task to Redis broker
        |
        v
Worker executes clone task
        |
        v
Update repository and job statuses
        |
        v
GET /api/v1/jobs/{job_id}
```

Redis is the Celery broker. PostgreSQL remains the source of truth for repositories and jobs. The API must return after enqueueing the task; it must not wait for the worker to finish.

## What Each Part Does

### FastAPI application

The FastAPI process handles HTTP requests only. It authenticates the user, validates the repository ID, creates the database job record, publishes the task, and returns the job reference.

The API process does not clone repositories. It must remain responsive while workers process jobs in the background.

### PostgreSQL

PostgreSQL stores the durable state of the system:

- Which repository owns the job.
- Which user owns the repository.
- Which job status is current.
- Which Celery task represents the job.
- When execution started and finished.
- Why a job failed, when a safe error is available.

Redis and Celery may lose transient runtime state. The database record must still be sufficient for the API to report the last known job state.

### Redis

Redis is the message broker between the API and the worker:

1. The API publishes a task message to Redis.
2. Redis holds the message until a worker is available.
3. A Celery worker consumes the message.
4. Celery acknowledges or retries the task according to its configuration.

Redis is not the source of truth for job history. It only transports work.

### Celery application

The Celery application is the shared task registry and broker configuration.

It must be importable in two processes:

- The FastAPI process, to enqueue tasks.
- The worker process, to discover and execute tasks.

The Celery application should not import the FastAPI application object. This prevents circular imports and keeps worker startup independent from HTTP server startup.

### Worker process

The worker is a separate process from FastAPI. It listens to the Redis broker and executes registered tasks.

The worker performs repository cloning in this milestone.
It does not parse, embed, graph, or analyze source code yet.

### Job service

The job service is the database boundary for job state. Routes and tasks should call the service instead of writing job fields directly.

The service is responsible for:

- Creating a job for an owned repository.
- Saving the Celery task ID after enqueueing.
- Loading a job only when the authenticated user owns its repository.
- Moving a job from `queued` to `running`.
- Moving a job to `completed` or `failed`.
- Setting timestamps consistently.
- Clearing or preserving error information according to the transition.

This boundary allows the clone-first task to be extended later without changing the public API.

## Detailed Request Lifecycle

### Starting an indexing job

When the client calls `POST /api/v1/repositories/{repository_id}/index`:

1. FastAPI extracts the CodeDNA JWT.
2. The authentication dependency resolves the local user.
3. The repository service loads the repository using both `repository_id` and `owner_id`.
4. If no owned repository exists, the route returns `404`.
5. The job service creates a PostgreSQL row with `status=queued` and `job_type=repository_index`.
6. The API publishes a Celery task containing the job ID and repository ID.
7. The job service stores the returned Celery task ID.
8. The API returns the job ID and `queued` status.
9. The request ends without waiting for the worker.

The database transaction and enqueue operation need an explicit failure policy. The safest initial policy is to create the job, enqueue the task, save the task ID, and mark the job failed if publishing fails. The implementation must not return `queued` when no task was published.

### Worker execution

When the worker receives the task:

1. The task opens a short-lived database session.
2. It loads the job by job ID.
3. It verifies that the job references the expected repository.
4. It marks the job `running` and records `started_at`.
5. It changes the repository status to `cloning`.
6. It shallow-clones the repository into the configured worker workspace.
7. It marks the job `completed` and records `completed_at`.
8. It changes the repository status to `ready`.
9. It stores internal clone metadata.
10. It commits the final transaction and closes the database session.

If an exception occurs:

1. The task catches the failure at the task boundary.
2. It marks the job `failed`.
3. It stores a safe, non-secret error message.
4. It changes the repository status to `failed`.
5. It commits the failure state.
6. It re-raises only if the configured Celery retry policy requires another attempt.

The task must never store access tokens, client secrets, database URLs, or full exception payloads in `error_message`.

### Reading a job status

When the client calls `GET /api/v1/jobs/{job_id}`:

1. FastAPI validates the JWT.
2. The job service queries the job joined to its repository.
3. The query includes the authenticated owner ID.
4. A missing job or a job owned by another user returns `404`.
5. A visible job is serialized through a response schema.

The API reports the database state, not an unaudited value read directly from Redis.

## Job Data Model

The initial job model should remain deliberately small.

| Field | Purpose |
| --- | --- |
| `id` | Stable public job identifier. |
| `repository_id` | Repository being processed. |
| `job_type` | Identifies the work, initially `repository_index`. |
| `status` | Durable lifecycle state. |
| `celery_task_id` | Operational ID returned by Celery. |
| `error_message` | Safe failure summary, nullable. |
| `started_at` | Time worker execution began, nullable. |
| `completed_at` | Time execution completed or failed, nullable. |
| `created_at` | Time the API created the job. |
| `updated_at` | Time the job record was last changed. |

The job should have a foreign key to `repositories.id`. The repository ownership check remains necessary even if a future job table also stores `owner_id`, because the repository relationship is the authoritative ownership boundary for this workflow.

## Status Transitions

### Job status

```text
queued
  |
  v
running
  |
  +----> completed
  |
  +----> failed
```

The initial milestone should reject invalid transitions in the service layer. For example, a completed job should not silently move back to running.

### Repository status

The existing repository enum is reused:

```text
registered -> indexing -> ready
                    \
                     -> failed
```

The task moves from `registered` to `cloning`, then to `ready` or `failed`.

`archived` is not changed by the indexing task. An archived repository should be rejected or handled by an explicit future policy rather than silently reactivated.

## Implemented Module Structure

The implementation adds these boundaries:

```text
apps/api/app/
├── core/
│   └── celery.py              # Celery application and broker setup
├── db/
│   └── models/
│       └── job.py             # Job ORM model
├── modules/
│   ├── jobs/
│   │   ├── dependencies.py    # Job service dependency
│   │   ├── enums.py           # Job status and type enums
│   │   ├── interfaces.py      # Job service protocol
│   │   ├── router.py          # Job status endpoint
│   │   ├── schemas.py         # Job API schemas
│   │   └── service.py         # Job persistence and transitions
│   └── repositories/
│       └── router.py          # Index start endpoint
└── workers/
    ├── tasks.py               # Stub task entrypoint
    └── database.py            # Worker session lifecycle if needed
```

The exact filenames can follow existing project conventions, but the responsibilities should remain separate:

- Celery configuration must not contain repository business logic.
- Job service must not make GitHub API calls.
- Repository routes must not execute work synchronously.
- Tasks must not contain HTTP response logic.
- Schemas must not contain database queries.

## Configuration

The worker and API need the same broker configuration:

```text
REDIS_URL=redis://redis:6379/0
REPOSITORY_WORKSPACE_PATH=/var/lib/codna/repositories
```

The value must continue to come from `Settings`. The worker should receive it through Docker Compose environment injection in the same way as the API.

No new secret is required for public repository cloning. Private repository cloning depends on the backend-only GitHub token already stored from OAuth and on the scopes granted by the GitHub OAuth app.

## Implemented API Contract

### Start indexing

```http
POST /api/v1/repositories/{repository_id}/index
Authorization: Bearer <codedna-jwt>
```

Response:

```json
{
  "repository_id": "00000000-0000-0000-0000-000000000002",
  "job_id": "00000000-0000-0000-0000-000000000003",
  "status": "queued"
}
```

If a queued or running index job already exists for the repository, the API returns that existing job and does not enqueue another Celery task.

### Read job status

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <codedna-jwt>
```

The job is visible only when the authenticated user owns the linked repository.

## Database Migration

Alembic revision `20260717_000006_create_jobs_table.py` creates:

- PostgreSQL enum `job_status`: `queued`, `running`, `completed`, `failed`.
- PostgreSQL enum `job_type`: `repository_index`.
- Table `jobs`.
- Indexes for repository lookup, status filtering, type filtering, and Celery task lookup.

The `jobs.repository_id` foreign key cascades on repository deletion because jobs are operational history for that repository registration.

## Docker Process Model

The Compose services have separate responsibilities:

| Service | Responsibility |
| --- | --- |
| `api` | FastAPI HTTP server and task producer. |
| `redis` | Celery broker. |
| `postgres` | Durable application and job state. |
| `migrate` | Applies Alembic migrations before use. |
| `worker` | Celery task consumer and executor. |

The worker command must start Celery, not the FastAPI server and not a placeholder Python module. The API and worker must use compatible application code and configuration.

The worker should depend on healthy Redis and PostgreSQL services. It may start before the API because it does not need to serve HTTP traffic.

## Failure and Duplicate Policies

These policies should be explicit in the implementation.

### Queue failure

If Redis is unavailable while creating a job:

- Do not return `queued`.
- Mark the job `failed` if the row was already created.
- Return a controlled `503` or `502` response.

### Worker failure

If the worker task raises:

- Persist `failed` in the job record.
- Persist `failed` in the repository record.
- Store only a safe error summary.
- Keep timestamps available for diagnosis.

### Duplicate indexing request

The initial policy should be one of these and should be documented by the API:

- Return the currently active job when a queued/running job already exists.
- Return `409 Conflict` for an active duplicate.
- Allow a new job only after the previous job is completed or failed.

The recommended MVP policy is to return the active job so repeated frontend requests do not create duplicate work.

### Concurrent requests

Two simultaneous start requests must not create duplicate active jobs for the same repository. This requires either a database constraint for active jobs or a transaction-safe service check.

## What This Milestone Does Not Do

The worker must not yet:

- Synchronize branches, commits, issues, or pull requests.
- Walk the repository filesystem.
- Parse code with Tree-sitter.
- Generate semantic chunks.
- Call OpenAI or another embedding provider.
- Write pgvector embeddings.
- Create graph nodes or edges.
- Generate AI answers.

The clone-first task proves that a request can move through API, PostgreSQL, Redis, Celery, worker, Git, local workspace storage, and status polling successfully.

## Implementation Order

### 1. Celery application

Create a central Celery application module under the API infrastructure layer.

Responsibilities:

- Read the broker URL from `Settings`.
- Configure the Redis broker.
- Register task modules explicitly.
- Keep task imports independent from FastAPI route imports.

The Celery application should be importable by both the worker process and API-side enqueueing code.

### 2. Redis broker integration

Use the existing `REDIS_URL` setting. Do not create a second queue configuration or hardcode a Redis URL.

The existing FastAPI Redis client is used for application health and cache access. Celery uses the same Redis service through its broker configuration, but the two clients have separate responsibilities.

### 3. Job model and migration

Add a minimal `jobs` table. Suggested fields:

- `id` UUID primary key
- `repository_id` UUID foreign key
- `job_type`
- `status`
- `celery_task_id`
- `error_message` nullable
- `started_at` nullable
- `completed_at` nullable
- `created_at`
- `updated_at`

Initial job statuses:

```text
queued
running
completed
failed
```

The job record is the durable status record. Celery state is operational metadata and must not replace the database record.

### 4. Job service

The job service owns database operations:

- Create a queued job.
- Attach the Celery task ID.
- Mark a job running.
- Mark a job completed.
- Mark a job failed with a safe error message.
- Load a job scoped to the authenticated repository owner.

The service should expose stable interfaces so the clone-first task can later be extended into the real indexing pipeline.

### 5. Job router and status API

Add an authenticated job status endpoint:

```http
GET /api/v1/jobs/{job_id}
```

The response should contain the job ID, repository ID, type, status, task ID if available, timestamps, and error information when failed.

The endpoint must not expose another user's jobs. Ownership should be checked through the repository relationship or an owner field on the job record.

### 6. Worker startup

The worker container should start Celery using the shared application module, for example:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

Current command:

```bash
celery -A app.core.celery:celery_app worker --loglevel=INFO
```

The worker must depend on Redis and PostgreSQL being available. Database access from a task must use a short-lived async session and must always close the session.

### 7. Clone-first background task

The first task deliberately performs only the repository cloning stage:

1. Load the job and repository.
2. Mark the job `running`.
3. Set the repository status to `cloning`.
4. Shallow-clone the repository into the configured workspace.
5. Mark the job `completed`.
6. Set the repository status to `ready`.
7. Store internal clone path and `last_cloned_at`.

The task must not call GitHub synchronization APIs, parse files, generate embeddings, or build graph data.

## Public API Contract

### Start indexing

```http
POST /api/v1/repositories/{repository_id}/index
Authorization: Bearer <codedna-jwt>
```

Expected response:

```json
{
  "repository_id": "repository-uuid",
  "job_id": "job-uuid",
  "status": "queued"
}
```

The endpoint should return `404` if the repository does not belong to the authenticated user.

### Read job status

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <codedna-jwt>
```

Example completed response:

```json
{
  "id": "job-uuid",
  "repository_id": "repository-uuid",
  "job_type": "repository_index",
  "status": "completed",
  "celery_task_id": "celery-task-id",
  "error_message": null,
  "started_at": "2026-07-17T21:00:00Z",
  "completed_at": "2026-07-17T21:00:01Z",
  "created_at": "2026-07-17T21:00:00Z",
  "updated_at": "2026-07-17T21:00:01Z"
}
```

## Verification Plan

Once implemented, verify the infrastructure in this order.

### 1. Start the infrastructure

```bash
API_PORT=8001 docker compose up -d --build api postgres redis worker
docker compose run --rm --build migrate
```

### 2. Confirm the worker is running

```bash
docker compose ps
docker compose logs --tail=100 worker
```

The worker should connect to Redis and report that it is ready to receive tasks.

### 3. Start a job

Use a repository already imported through GitHub discovery:

```bash
curl -i -X POST \
  "http://localhost:8001/api/v1/repositories/{repository_id}/index" \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

Expected status: `202 Accepted` or the agreed asynchronous success status, with `status` equal to `queued`.

### 4. Poll job status

```bash
curl -i \
  "http://localhost:8001/api/v1/jobs/{job_id}" \
  -H "Authorization: Bearer ${CODEDNA_TOKEN}"
```

The expected sequence is:

```text
queued -> running -> completed
```

The repository should end in `ready` after the clone-first task completes.

### 5. Verify failure and ownership behavior

Test that:

- Requests without a JWT return `401`.
- A job belonging to another user returns `404`.
- A missing repository returns `404`.
- Worker failures produce a `failed` job and repository status `failed`.
- Repeating the request follows an explicit duplicate-job policy.

## Testing Requirements

The milestone should include tests for:

- Celery application broker configuration.
- Job creation and queued response.
- Celery task enqueueing with the expected payload.
- Job status lookup.
- Unauthorized job access.
- Missing repository handling.
- Clone task success transitions.
- Clone task failure transitions.

The tests should mock Celery enqueueing and use isolated database/service boundaries. They should not require a live GitHub API.

## Future Replacement

The public onboarding contract should remain unchanged when clone-first indexing is extended:

```text
Repository onboarding
        |
        v
Job record + Celery task
        |
        v
Clone repository
        |
        v
Parse with Tree-sitter
        |
        v
Chunk and embed
        |
        v
Build graph and mark ready
```

Only the task implementation and supporting pipeline services should change. The repository onboarding route, job status route, job record, and task identity should remain stable.

## Milestone Acceptance Criteria

The milestone is complete only when all of the following are true:

- The API can create a job for an authenticated repository owner.
- The API returns a stable `job_id` and `queued` status.
- The task is visible to and consumed by the Celery worker.
- The worker can update PostgreSQL job state.
- The worker can update repository state.
- The status endpoint reports queued, running, completed, and failed states correctly.
- Unauthorized users cannot start or read jobs.
- Duplicate active indexing requests follow the documented policy.
- API, worker, Redis, PostgreSQL, and migration containers work together in Docker.
- Tests cover producer behavior, task transitions, failure handling, and ownership checks.
- Extending the clone-first task does not require changing the public API contract.
