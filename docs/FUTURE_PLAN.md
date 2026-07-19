# CodeDNA Delivery Plan

## Current State

Repository indexing now creates durable inventory, parse results, extracted knowledge items, and repository-aware semantic chunks. Chunks include source content, source ranges, stable identifiers, static-analysis metadata, and deterministic local relationships. Chunk embeddings and owner-scoped hybrid retrieval are available.

The current system intentionally has no LLM answer generation, chat, graph persistence, repository-history ingestion, or incremental indexing. Retrieval is production-shaped search, not yet a natural-language answer service.

## Product Positioning and Differentiation

CodeDNA is not "chat with a codebase." It explains why a codebase is shaped the
way it is, using source-backed evidence and change-impact context.

The product must make this promise concrete:

- Every answer is citation-first: repository path, exact line range, and stable chunk ID.
- Answers use structured repository knowledge, not an unbounded dump of source files.
- Dependency, caller, importer, reference, and impact paths are first-class product data.
- Repository history, pull requests, issues, and documented decisions eventually explain *why*, not only *what*.
- Private repository data remains owner-scoped and provider credentials are never persisted.
- Re-indexing changed repositories is incremental, keeping repeat use fast and model costs bounded.

## Cost and Reliability Principles

- Generate an embedding only when a chunk source hash or revision changes; never on every search.
- Use lexical retrieval and metadata filters before vector search, then pass only bounded top results to an LLM.
- Cache repeat retrieval and answer requests where safe, with explicit invalidation after indexing.
- Use the least expensive capable model for routing and extraction; reserve answer-generation models for final responses.
- Enforce application-level per-user and per-repository request, context, and spend limits before public chat is enabled.
- Track provider usage without storing API keys, raw access tokens, or private repository credentials.

## Next Backend Milestones

### 1. Embeddings and Retrieval

- Completed 2026-07-19: chunk embedding job reads `repository_chunks` only.
- Completed 2026-07-19: vectors are stored by chunk ID in PostgreSQL/pgvector with repository, source-type, and chunk-type filters.
- Completed 2026-07-19: repository-scoped hybrid lexical/vector retrieval is available at `GET /api/v1/repositories/{repository_id}/search`.
- Completed 2026-07-19: embedding generation is idempotent by source hash and embedding model.
- Completed 2026-07-19: exact code-symbol queries boost matching chunk titles, so a class or function definition ranks ahead of files that only import or use it.

### 2. Repository Question API — Next

- Add a repository-scoped question endpoint that builds on the existing search endpoint; keep search available as the transparent debugging/evidence API.
- Retrieve relevant chunks first, then construct bounded context for an LLM provider.
- Return a concise answer plus mandatory citations containing chunk IDs, paths, and line ranges.
- If evidence is insufficient or conflicting, say so and return the best matching citations rather than inventing an answer.
- Persist request status and safe telemetry, never provider credentials or raw private repository tokens.
- Add per-user and per-repository rate, context, and spend guards before enabling public access.
- Cache citation-preserving answers and invalidate them after repository re-indexing.

### 3. Persistent Relationship Graph

- Materialize the existing chunk relationships into graph tables or a graph projection.
- Add dependency, caller, importer, and impact traversal endpoints.
- Preserve unresolved and dynamic relationships as probabilistic or unresolved facts rather than asserting them as certain.

### 4. Incremental Indexing

- Compare repository revision and file hashes before parsing.
- Rebuild knowledge and chunks only for changed files plus affected relationship edges.
- Delete stale rows for removed files in the same transaction.

### 5. Repository History and Decision Context

- Ingest owner-authorized commit history, pull requests, issues, and discussion metadata.
- Link historical artifacts to affected paths, chunks, symbols, and relationships where evidence supports it.
- Distinguish facts from inferred rationale; preserve uncertainty when links are incomplete.
- Add timeline and "why does this exist?" retrieval that returns source and history citations together.

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
- Show cost-safe limits and clear retry states without exposing provider details.

### 4. Architecture and Impact

- Build an impact view from persistent graph traversal: callers, imports, references, and affected chunks.
- Make every graph node linkable back to a repository path, line range, and stable chunk ID.
- Add a timeline view only after repository history and decision context are available.

## Release Checklist

- Run backend tests and database migrations in CI.
- Re-index representative Python, TypeScript, documentation-heavy, Prisma, and configuration-heavy repositories.
- Verify chunk metadata for imports, calls, references, exports, and unresolved relationships.
- Verify private repository access remains owner-scoped.
- Build and smoke-test API, worker, migrate, and frontend containers before deployment.
