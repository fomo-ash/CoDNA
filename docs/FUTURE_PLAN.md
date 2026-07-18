# CodeDNA Delivery Plan

## Current State

Repository indexing now creates durable inventory, parse results, extracted knowledge items, and repository-aware semantic chunks. Chunks include source content, source ranges, stable identifiers, static-analysis metadata, and deterministic local relationships.

The current system intentionally has no embeddings, vector database, retrieval, LLM calls, chat, or graph persistence.

## Next Backend Milestones

### 1. Embeddings and Retrieval

- Add a chunk embedding job that reads `repository_chunks` only.
- Store vectors with chunk IDs and metadata filters in PostgreSQL/pgvector.
- Add lexical plus vector retrieval with repository and source-type filtering.
- Keep embedding generation idempotent by source hash or chunk revision.

### 2. Repository Question API

- Add a repository-scoped query endpoint.
- Retrieve relevant chunks first, then construct bounded context for an LLM provider.
- Return answer citations containing chunk IDs, paths, and line ranges.
- Persist request status and safe telemetry, never provider credentials or raw private repository tokens.

### 3. Persistent Relationship Graph

- Materialize the existing chunk relationships into graph tables or a graph projection.
- Add dependency, caller, importer, and impact traversal endpoints.
- Preserve unresolved and dynamic relationships as probabilistic or unresolved facts rather than asserting them as certain.

### 4. Incremental Indexing

- Compare repository revision and file hashes before parsing.
- Rebuild knowledge and chunks only for changed files plus affected relationship edges.
- Delete stale rows for removed files in the same transaction.

## Frontend Integration Plan

### 1. Repository Indexing View

- List imported repositories and current job/repository status.
- Start indexing and poll the existing job endpoint until completion or failure.
- Present safe worker error summaries and a retry action.

### 2. Repository Explorer

- Add inventory, parse-result, knowledge-item, and chunk tabs using the existing owner-scoped APIs.
- Show chunk metadata, source content, relationships, and source line ranges.
- Link relationship targets to their matching chunk where a stable ID resolves.

### 3. Search and Chat

- Build these only after the retrieval API is complete.
- Keep UI answers citation-first: each answer links to repository path, line range, and chunk ID.
- Do not call model providers directly from the browser.

## Release Checklist

- Run backend tests and database migrations in CI.
- Re-index representative Python, TypeScript, documentation-heavy, Prisma, and configuration-heavy repositories.
- Verify chunk metadata for imports, calls, references, exports, and unresolved relationships.
- Verify private repository access remains owner-scoped.
- Build and smoke-test API, worker, migrate, and frontend containers before deployment.
