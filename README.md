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
│       └── repositories/
├── alembic/
└── tests/
```

## Backend Verification

Start the local API and dependencies:

```bash
API_PORT=8001 docker compose up -d --build api postgres redis
docker compose run --rm --build migrate
```

The current discovery/import API is documented in [docs/API.md](docs/API.md). Follow [docs/REPOSITORY_REGISTRATION.md](docs/REPOSITORY_REGISTRATION.md) for OAuth setup, exact `curl` checks, migration verification, and test commands.
