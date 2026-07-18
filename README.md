# 🧬 CoDNA

> Every codebase has a DNA. We help you decode it.

## Overview

CoDNA is an AI-powered software intelligence platform that enables developers to understand complex codebases by analyzing source code, commit history, pull requests, issues, and documentation.

Instead of simply answering *what* the code does, CoDNA explains *why* it exists.

## Current Progress

- ✅ Monorepo initialized
- ✅ Next.js frontend setup
- ✅ Turborepo configured
- ✅ npm Workspaces configured
- ✅ Project documentation initialized
- ✅ FastAPI, PostgreSQL, Redis, and Alembic foundation
- ✅ GitHub OAuth authentication with backend-only token storage
- ✅ GitHub repository discovery and owner-scoped import
- ✅ Celery/Redis asynchronous indexing scaffold with persisted job status
- ✅ Repository cloning scaffold with worker-managed local workspace
- ✅ Repository file inventory and Tree-sitter parse metadata for Python, JavaScript, TypeScript, and TSX
- ✅ Structured repository knowledge extraction for source code, Markdown docs, Prisma schema, and project configuration

## Tech Stack

### Frontend
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

### Monorepo
- npm Workspaces
- Turborepo

### Planned Backend
- FastAPI
- PostgreSQL
- Redis
- OpenAI
- Tree-sitter
- pgvector

## Repository Structure

```text
apps/api/
├── app/
│   ├── api/v1/
│   ├── core/
│   ├── db/
│   └── modules/
│       ├── auth/
│       ├── github/
│       ├── jobs/
│       └── repositories/
├── alembic/
└── tests/
```

## Backend Verification

Start the local API and dependencies:

```bash
docker compose build api worker migrate
docker compose up -d postgres redis
docker compose run --rm --build migrate
API_PORT=8001 docker compose up -d api worker
```

Use `API_PORT=8001` when local port `8000` is already allocated.

Useful docs:

- [API reference](docs/API.md)
- [Beginner backend verification guide](docs/BACKEND_VERIFICATION_GUIDE.md)
- [Frontend teammate workplan](docs/FRONTEND_TEAMMATE_WORKPLAN.md)
- [AI demo cost policy](docs/AI_COST_POLICY.md)
- [Repository registration details](docs/REPOSITORY_REGISTRATION.md)
- [Async indexing architecture](docs/ASYNC_INDEXING.md)
