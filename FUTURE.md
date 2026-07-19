# CodeDNA future work

This document separates the local, low-cost repository intelligence path from
provider-backed features and records the next implementation priorities.

## Product tiers

### Free core

The following work runs in CodeDNA's own API and worker infrastructure and
does not require an OpenAI or Google AI request:

- GitHub sign-in and public repository import
- cloning and file discovery
- parsing, knowledge extraction, and semantic chunk construction
- file, parse-result, knowledge, chunk, and history explorers
- lexical retrieval, including filename and path search
- GitHub commit, pull request, and issue history ingestion

The free tier should apply repository-size, file-count, indexing-frequency,
and retention limits so worker and storage costs stay predictable.

### Provider-backed features

These features require a configured model provider and should be paid,
trial-limited, or available through a bring-your-own-key option:

- embeddings and semantic/hybrid retrieval
- generated repository Q&A
- any future model-based summaries or change explanations

Provider credentials remain server-side. The browser receives only CodeDNA's
session JWT and never an OpenAI, Google, or GitHub OAuth secret.

## Deployment architecture

CodeDNA needs more than a frontend host:

- **Web**: Next.js application
- **API**: FastAPI application and GitHub OAuth callback handling
- **Worker**: Celery worker for clone, index, history, and embedding tasks
- **PostgreSQL + pgvector**: application data, chunks, history, embeddings,
  answer cache, and usage tracking
- **Redis**: Celery broker and job coordination
- **Persistent repository storage**: a durable volume for development or an
  object-storage-backed workspace strategy for production

Supabase is optional. It can host PostgreSQL and pgvector, but it does not
replace Redis, the worker runtime, or persistent repository storage. Supabase
Auth is also optional because CodeDNA currently owns GitHub OAuth and issues
its own session JWTs.

Suggested first production topology:

- Supabase PostgreSQL with pgvector enabled
- Redis Cloud or Upstash Redis
- API, worker, and web deployed as separate Docker services on Railway,
  Render, Fly.io, or equivalent
- S3/R2-compatible object storage for durable repository workspaces
- GitHub OAuth app configured with the production web callback URL

## Product roadmap

### Repository history

- Add per-file history using `git log -- <path>`.
- Add symbol-level introduction and change history where parser metadata can
  identify the relevant source range.
- Link history artifacts to changed paths and chunks instead of presenting a
  repository-wide timeline only.
- Add pagination and refresh controls; current ingestion is intentionally
  bounded to GitHub's latest history page per artifact type.

### Retrieval and Q&A

- Add a user-visible embedding retry/status action everywhere repositories are
  listed.
- Add an explicit lexical-only mode when no embedding provider is configured.
- Make Q&A explain when generation is unavailable rather than presenting a
  generic failure.
- Add file/symbol-aware impact paths with autocomplete.
- Add evaluation fixtures for factuality, citation coverage, and irrelevant
  context rejection.

### Security and operations

- Use HTTPS and production-only CORS origins.
- Rotate and store provider/GitHub secrets in the deployment platform's secret
  manager, never in committed `.env` files.
- Add request rate limits, repository quotas, worker concurrency limits, and
  per-user spend caps.
- Add structured audit logs and error monitoring.
- Add backup, retention, deletion, and user data-export policies.

### Testing before production

- API tests for GitHub OAuth, repository ownership isolation, public import,
  history access, embedding retry, and provider failure fallback.
- Worker integration tests for indexing, history ingestion, and embedding
  status transitions.
- Browser end-to-end tests for login, import, index, lexical search, semantic
  search, Q&A citations, and history links.
- A staging deployment with real GitHub OAuth and a non-production provider
  budget cap.
