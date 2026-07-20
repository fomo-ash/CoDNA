# CodeDNA Delivery Plan

> **Status:** Current implementation and next work
> **Last reviewed:** 2026-07-20

## Current state

CodeDNA currently supports GitHub OAuth, owner-scoped repository registration, asynchronous Celery indexing, safe inventory, Tree-sitter parsing, structured knowledge extraction, semantic chunks, repository-local relationship edges, history artifacts, incremental re-indexing, optional pgvector embeddings, hybrid retrieval, graph/impact traversal, and cited repository Q&A.

The browser already includes repository import, indexing status, explorer tabs for files/parses/knowledge/history/chunks, retrieval search, impact controls, chunk citation links, and question answering when a provider is configured.

## Product principles

- Prefer source evidence for runtime and implementation questions; use documentation as intent, not runtime proof.
- Cite repository path, line range, and stable chunk ID for generated answers.
- Preserve unresolved or dynamic relationships as unresolved rather than inventing a dependency path.
- Keep provider keys and GitHub tokens server-side; scope repository data to its owner.
- Keep lexical retrieval available when embeddings or a model provider are unavailable.
- Re-index incrementally, and invalidate answer cache entries when indexed evidence changes.

## Next priorities

### 1. Evaluation and answer quality

- Add representative repository fixtures and scored evaluations for citation coverage, factuality, evidence boundaries, and answer usefulness.
- Test source-first versus documentation-first retrieval decisions across runtime, configuration, architecture, and API questions.
- Improve graceful handling for missing evidence, dynamic framework wiring, and unresolved imports.

### 2. Graph confidence and explanation

- Validate multi-hop path and symbol-impact traversal across representative Python and TypeScript repositories.
- Add confidence and relationship-kind explanations without presenting static analysis as complete runtime discovery.
- Make graph evidence easier to inspect from a cited chunk or impact result.

### 3. History and decision context

- Link commits, issues, and pull requests to paths, chunks, and symbols only when repository evidence supports the connection.
- Add timeline-oriented exploration and combined source/history answers for questions about why a change exists.

### 4. Product hardening

- Add browser-level end-to-end coverage for sign-in, import, indexing, retrieval, impact, and cited answers.
- Add production-ready rate limits, quotas, auditability, retention/deletion controls, backups, monitoring, and alerting.
- Validate deployment with HTTPS OAuth callbacks, restricted CORS origins, durable worker storage, and explicit cost limits.

### 5. Broader repository support

- Add more language parsers and improve import resolution for aliases, package layouts, and framework conventions.
- Add organization-aware access controls and carefully scoped cross-repository workflows.
- Explore an IDE extension that surfaces repository-aware search, impact paths, history, and cited answers beside the current file.

## Explicit non-goals for the next release

- Do not claim exhaustive runtime dependency analysis from static evidence.
- Do not expose GitHub tokens or model-provider credentials to the browser.
- Do not make public deployment the default until request, spend, and retention controls are in place.
