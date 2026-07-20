# GitHub Repository Registration and Ownership

> **Status:** Current implementation
> **Last reviewed:** 2026-07-20

## Purpose

Registration imports GitHub metadata into CodeDNA under the authenticated user. Registration is deliberately separate from indexing: import is a short API request; cloning and analysis begin only when the caller starts an index job.

## Flow

```text
Browser
  ↓ GitHub OAuth
CodeDNA auth callback
  ↓ CodeDNA JWT
Authenticated repository import
  ↓ GitHub API metadata lookup
Owner-scoped repository record
  ↓ explicit index request
Durable job + Celery worker
```

## Authentication and ownership

- `GET /api/v1/auth/github/login` starts GitHub OAuth.
- The callback returns a CodeDNA JWT. The browser uses it as `Authorization: Bearer <codedna-jwt>`.
- The backend retains the GitHub access token on the user record. It is not returned in CodeDNA API responses.
- `owner_id` is read from the JWT-backed user dependency, never from the import payload.
- Repository, job, file, parse, knowledge, chunk, history, retrieval, graph, and question APIs are owner-scoped.

## Registration endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/github/me` | Read the connected GitHub profile |
| `GET` | `/api/v1/github/repositories` | Browse repositories accessible to that GitHub user |
| `POST` | `/api/v1/repositories` | Register one GitHub repository |
| `GET` | `/api/v1/repositories` | List the caller's registered repositories |
| `GET` | `/api/v1/repositories/{repository_id}` | Read one caller-owned repository |
| `POST` | `/api/v1/repositories/{repository_id}/index` | Start or reuse an asynchronous index job |

The import payload accepts exactly one identifier:

```json
{ "github_id": "12345" }
```

or:

```json
{ "full_name": "owner/repository" }
```

The backend obtains canonical name, clone URL, default branch, visibility, and GitHub ID from GitHub before persistence. The client cannot submit `owner_id`, clone credentials, clone URL, status, or arbitrary repository metadata.

## What follows registration

Registration creates a repository with status `registered`. Indexing then runs asynchronously through Celery and Redis:

```text
clone → inventory → parse → knowledge → chunks → history → optional embeddings
```

The initial index job may be reused when a queued or running job already exists. A later re-index uses the same entry point and incrementally processes changed paths.

## Error behavior

| Situation | Response |
| --- | --- |
| Missing or invalid CodeDNA JWT | `401 Unauthorized` |
| Missing GitHub authorization | `401 Unauthorized` |
| Invalid import payload | `422 Unprocessable Entity` |
| GitHub repository not found or inaccessible | `404 Not Found` |
| Caller does not own the CodeDNA repository | `404 Not Found` |
| GitHub API failure | `502 Bad Gateway` |
| Already registered repository | `409 Conflict` |
| Index task cannot be enqueued | `503 Service Unavailable` |

## Verification

Start the local stack and apply migrations as described in [SETUP.md](../SETUP.md). Then authenticate in the web app, import a repository, start indexing, and observe the job status through `GET /api/v1/jobs/{job_id}` or the repository UI.

The current Alembic chain includes repository inventory, parse, knowledge, chunks, embeddings, answer cache/usage, relationship edges, history, and embedding-status migrations through revision `20260719_000018`.
