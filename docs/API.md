# CodeDNA API

> **Status:** Current implementation
> **Last reviewed:** 2026-07-20

## Base URL and authentication

The local API is normally available at `http://localhost:8001`; all application routes are under `/api/v1`.

Start GitHub OAuth with:

```http
GET /api/v1/auth/github/login
```

After the callback, clients use the backend-issued CodeDNA JWT:

```http
Authorization: Bearer <codedna-jwt>
```

The GitHub access token remains backend-side. Every repository-scoped route below requires the authenticated caller to own the repository.

## Authentication and GitHub

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/auth/github/login` | Begin GitHub OAuth |
| `GET` | `/auth/github/callback` | Complete OAuth and return CodeDNA JWT |
| `GET` | `/auth/me` | Read current CodeDNA user |
| `GET` | `/github/me` | Read connected GitHub profile |
| `GET` | `/github/repositories` | Browse GitHub repositories available to the caller |

`/github/repositories` accepts `visibility`, `sort`, `page`, and `per_page` (`1`–`100`).

## Repository registration and jobs

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/repositories` | Register a GitHub repository |
| `GET` | `/repositories` | List caller-owned repositories |
| `GET` | `/repositories/{repository_id}` | Read one repository |
| `POST` | `/repositories/{repository_id}/index` | Create or reuse an index job |
| `POST` | `/repositories/{repository_id}/embeddings/retry` | Retry a failed embedding run |
| `GET` | `/jobs/{job_id}` | Read an owner-scoped job |

Register with exactly one identifier:

```json
{ "github_id": "12345" }
```

or:

```json
{ "full_name": "owner/repository" }
```

The API fetches canonical GitHub metadata. It rejects client-supplied ownership, clone URL, visibility, status, and credentials.

### Start indexing

```http
POST /api/v1/repositories/{repository_id}/index
```

The response is `202 Accepted` and contains a repository ID, job ID, and job status. The API enqueues Celery work through Redis; it does not clone or parse inside the request. The worker performs clone, inventory, incremental parsing, knowledge extraction, chunk rebuild, relationship derivation, history refresh, and optionally enqueues embeddings.

## Repository explorer

| Method | Endpoint | Query controls |
| --- | --- | --- |
| `GET` | `/repositories/{id}/files` | `page`, `page_size`, `language`, `extension`, `path_prefix` |
| `GET` | `/repositories/{id}/stats` | — |
| `GET` | `/repositories/{id}/parse-results` | `page`, `page_size`, `status`, `language`, `path_prefix` |
| `GET` | `/repositories/{id}/knowledge` | `page`, `page_size`, `source_type`, `item_type`, `path_prefix` |
| `GET` | `/repositories/{id}/chunks` | `page`, `page_size`, `source_type`, `chunk_type`, `search` |
| `GET` | `/chunks/{chunk_id}` | — |
| `GET` | `/repositories/{id}/history` | `limit` (`1`–`500`) |

Files return inventory metadata rather than raw clone paths. Parse results expose Tree-sitter status, symbols, imports, diagnostics, and language details. Knowledge items provide extracted structured facts. Chunks are citation-ready semantic evidence with source range, content, type, and relationship metadata.

The chunk listing `search` filter matches path, title, and content. Citation IDs are stable references used to open the exact persisted chunk and to connect answers back to their source evidence.

## Retrieval

```http
GET /api/v1/repositories/{repository_id}/search
```

Required query parameter: `query` (1–1000 characters).

Optional controls:

| Parameter | Range / purpose |
| --- | --- |
| `source_type` | Limit evidence to a source category such as `source_code` or `documentation` |
| `chunk_type` | Limit evidence to a semantic chunk type |
| `limit` | `1`–`100`, default `20` |

Retrieval combines lexical evidence with vector similarity when repository embeddings are available. It returns chunk evidence and per-result lexical/vector scores. If embeddings are unavailable or failed, lexical retrieval remains usable.

## Graph and impact

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/repositories/{id}/graph` | Read repository-local relationship edges; `limit` is `1`–`2000` |
| `GET` | `/repositories/{id}/impact` | Direct impact analysis by `path` |
| `GET` | `/repositories/{id}/impact/traverse` | Bounded path traversal by `path` and `depth` |
| `GET` | `/repositories/{id}/impact/symbol` | Bounded traversal by `stable_symbol_id` and `depth` |

Traversal depth is one to three. These endpoints expose resolved static repository relationships; they do not guarantee discovery of dynamic imports, framework registration, reflection, or external-service dependencies.

## Questions and impact explanations

| Method | Endpoint | Body |
| --- | --- | --- |
| `POST` | `/repositories/{id}/questions` | `question`, optional `impact_path`, optional `impact_depth` |
| `POST` | `/repositories/{id}/impact/explain` | `path`, optional `question`, optional `depth` |

Question answers are generated from indexed evidence and include citations. Runtime, implementation, configuration, authentication, dependency, and impact questions prefer source-code evidence when it is available. Documentation may explain intended behavior, but it is not treated as proof of an unobserved runtime path.

Question requests can return:

| Status | Meaning |
| --- | --- |
| `429` | Answer-provider or configured answer-budget limit reached |
| `502` | Answer provider failed |
| `503` | Required answer or embedding configuration is unavailable |

## Health

```http
GET /api/v1/health
GET /api/v1/live
GET /api/v1/ready
```

`ready` verifies the API's database and Redis dependencies.

## Common errors

| Status | Meaning |
| --- | --- |
| `401` | Missing/invalid CodeDNA JWT or missing GitHub authorization |
| `404` | Resource missing, inaccessible on GitHub, or not owned by the caller |
| `409` | Duplicate repository import or invalid embedding-retry state |
| `422` | Invalid path, payload, or query parameter |
| `429` | Answer request limited by provider/budget |
| `502` | GitHub or answer-provider failure |
| `503` | Queue, answer provider, or embedding configuration unavailable |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the worker and data-flow design, and [SETUP.md](../SETUP.md) for local setup.
