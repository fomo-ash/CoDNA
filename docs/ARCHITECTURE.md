# CodeDNA Architecture

> **Status:** Current implementation
> **Last reviewed:** 2026-07-20

## Purpose

CodeDNA indexes a GitHub repository and makes its implementation evidence searchable. It supports repository inventory, parsing, knowledge extraction, semantic chunks, embeddings, hybrid retrieval, relationship traversal, history artifacts, and grounded repository questions.

The product is an analysis tool, not a code editor or an autonomous code-writing agent. Answers are grounded in indexed repository chunks and return citations to the relevant path, line range, and chunk identifier.

## Running system

```text
Browser (Next.js, port 3333)
        |
        | CodeDNA JWT
        v
FastAPI application (port 8001)
        |
        +-- GitHub OAuth and repository APIs
        +-- Browse APIs: files, parses, knowledge, chunks, history
        +-- Retrieval, graph traversal, and question APIs
        |
        +-- Redis / Celery enqueue
                 |
                 v
           Celery worker
                 |
                 +-- clone repository
                 +-- inventory and incremental parse
                 +-- knowledge extraction and chunks
                 +-- history refresh
                 +-- optional embedding task
        |
        v
PostgreSQL + pgvector
```

The API and worker are Python applications in `apps/api`. They are modular within one deployable API application; they are not separate microservices. Docker Compose runs the API, worker, Postgres, and Redis locally.

## Ownership and authentication

GitHub OAuth begins at `GET /api/v1/auth/github/login`. The callback creates a CodeDNA JWT for the browser; the GitHub access token remains on the backend user record and is never returned to the frontend.

Protected routes use the CodeDNA JWT. `AuthContextMiddleware` opportunistically decodes a Bearer token into `request.state.auth`; protected route dependencies separately require a valid token and a `sub` claim. Repository reads and writes are owner-scoped, so a caller cannot access another user's imported repository data.

## Indexing flow

Indexing is asynchronous. `POST /api/v1/repositories/{repository_id}/index` creates or reuses a durable job, enqueues a Celery task through Redis, and returns `202 Accepted` without waiting for repository work.

```text
Index request
  ↓
Job record + Celery enqueue
  ↓
Shallow clone (worker workspace)
  ↓
File inventory and change detection
  ↓
Tree-sitter parsing of changed supported files
  ↓
Structured knowledge extraction
  ↓
Semantic chunk rebuild + relationship edges
  ↓
GitHub history refresh
  ↓
Job complete; repository remains searchable
  ↓
Optional, separate embedding job
```

The worker preserves inventory and parses for unchanged files, then rebuilds analysis for changed paths and known dependent paths. Embedding failure does not invalidate the completed repository index: lexical search and browse APIs remain available.

## Data model and responsibilities

| Layer | Primary stored records | Responsibility |
| --- | --- | --- |
| Repository | users, repositories, jobs | OAuth ownership, repository metadata, async job state |
| Inventory | repository_files, repository_statistics | Safe file list, hashes, language hints, aggregate counts |
| Parsing | repository_file_parses | Tree-sitter status, symbols, imports, diagnostics |
| Knowledge | repository_knowledge_items | Extracted source, documentation, configuration, and schema facts |
| Chunks | repository_chunks | Citation-ready semantic evidence with source ranges and metadata |
| Embeddings | repository_chunk_embeddings | Vector representations for configured embedding provider/model |
| Relationships | repository_relationship_edges | Repository-local resolved relationships used for graph and impact queries |
| History | repository_history_artifacts | GitHub commit, issue, and pull-request artifacts when accessible |
| Answers | repository_question_cache, repository_answer_usage | Cached grounded answers and provider-budget accounting |

PostgreSQL is the system of record. pgvector stores embedding vectors alongside repository data. Redis is used for Celery broker/backend communication; it is not the source of truth for repository analysis.

## Retrieval, graph, and answers

`GET /api/v1/repositories/{repository_id}/search` performs hybrid retrieval over indexed chunks. It combines lexical relevance with vector similarity when embeddings are available, applies optional source/chunk filters, and returns the evidence chunks and scores. If vector search is unavailable, the system can still return lexical results.

Relationship edges are persisted relationally and exposed through graph and impact endpoints. Impact traversal is bounded by a caller-selected depth of one to three; its results are evidence, not a claim that all runtime dependencies have been discovered.

`POST /api/v1/repositories/{repository_id}/questions` builds an answer from retrieved evidence. Runtime, implementation, configuration, authentication, dependency, and impact questions prefer source-code chunks first and fall back to mixed evidence only when source matches are unavailable. Documentation is treated as documented intent, not proof of runtime behavior. Answers include citations and respect cache, provider, token, and budget controls.

## Frontend

The Next.js frontend provides GitHub sign-in, repository import, dashboard, repository explorer, retrieval search, graph/impact exploration, chunk citations, and repository Q&A. It calls the backend through `apps/web/lib/api.ts`, which centralizes the API base URL, JWT attachment, response parsing, and error handling.

The repository explorer presents inventory, parse results, knowledge items, history artifacts, and chunks. It does not expose backend provider credentials, GitHub access tokens, local clone paths, or raw backend stack traces.

## Configuration and providers

Configuration is loaded by `app.core.config.Settings` and placed on application state during app creation. The API initializes database and Redis clients in its lifespan; middleware and routers are registered before handling requests.

The embedding service supports configured OpenAI or Google providers. The local default is OpenAI `text-embedding-3-small`. Repository answer generation also supports configured OpenAI or Google providers; the local default answer model is `gpt-5.4-mini`.

Provider keys remain server-side. An absent embedding provider leaves the repository browseable and lexically searchable; an answer request returns a configuration error if no answer provider is available.

## Explicit boundaries

The following are not currently implemented as product guarantees:

- a separate LangGraph or multi-agent orchestration layer;
- BullMQ or Node workers;
- Neo4j storage;
- live token streaming to the browser;
- cross-repository analysis;
- automatic architecture diagrams generated from unverified evidence;
- exhaustive runtime dependency discovery for dynamic imports, reflection, framework magic, or external services.

CodeDNA uses static repository evidence. It labels missing evidence instead of inventing callers, routes, or architecture.

## Operational characteristics

- API work that involves cloning, parsing, chunking, history, or embeddings runs in Celery workers.
- Health endpoints are available at `/api/v1/health`, `/api/v1/live`, and `/api/v1/ready`.
- The local Compose stack uses API port `8001` and web port `3333` when started with the documented environment values.
- Owner checks apply to repository, job, chunk, retrieval, graph, history, and question operations.

For endpoint-level contracts, see [API.md](API.md). For setup, see [SETUP.md](../SETUP.md).
