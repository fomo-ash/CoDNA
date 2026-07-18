# Frontend Teammate Workplan

## Purpose

This document defines what a frontend teammate can work on without blocking or breaking current backend development.

The backend is currently focused on:

- GitHub OAuth.
- Repository discovery.
- Repository import.
- Async indexing scaffolding.
- Job status tracking.

Frontend work can move in parallel if it stays inside the agreed boundaries below.

## Current Frontend State

The frontend is a Next.js application under:

```text
apps/web/
```

Current stack:

- Next.js 16.
- React 19.
- TypeScript.
- Tailwind CSS.
- App Router.

The current page is still close to the default starter screen.
That means the frontend teammate can safely shape the product UI.
She should not change backend contracts or shared infrastructure without coordination.

## Safe Work Areas

She can work on these areas independently:

| Area | Path | Notes |
| --- | --- | --- |
| Pages | `apps/web/app/` | Dashboard, auth callback page, repository screens. |
| Styling | `apps/web/app/globals.css` | Product theme, layout tokens, responsive styles. |
| Frontend components | `apps/web/components/` | Create this folder if needed. |
| Frontend utilities | `apps/web/lib/` | API client, auth token helpers, formatting helpers. |
| Frontend types | `apps/web/types/` | API response types. |
| Static frontend assets | `apps/web/public/` | Icons, placeholder assets, product visuals. |
| Frontend docs | `docs/` | UI notes, frontend verification, design decisions. |

These paths should not affect backend development if changes stay frontend-focused.

## Areas to Avoid Without Coordination

She should not modify these unless the backend owner agrees first:

| Area | Reason |
| --- | --- |
| `apps/api/` | Backend code, migrations, auth, jobs, repository APIs. |
| `docker-compose.yml` | Shared service wiring; changes can break local backend testing. |
| `infra/` | Shared Docker and deployment configuration. |
| `apps/api/.env.example` | Backend environment contract. |
| Alembic migrations | Database state must stay coordinated. |
| Backend API schemas | Frontend should consume the contract, not redefine it. |
| Root package tooling | `package.json`, `package-lock.json`, `turbo.json` can affect everyone. |

If she needs a dependency or root-level tooling change, she should open a small separate PR and explain why it is needed.

## Branch Workflow

Use separate branches.

Backend branch example:

```bash
git checkout -b backend/async-indexing
```

Frontend branch example:

```bash
git checkout -b frontend/dashboard-shell
```

Before starting frontend work:

```bash
git status
git pull
git checkout -b frontend/dashboard-shell
```

Before committing:

```bash
git status --short
git diff --stat
```

Do not use:

```bash
git add .
```

Use targeted staging instead:

```bash
git add apps/web docs/FRONTEND_TEAMMATE_WORKPLAN.md
```

If root files changed accidentally, inspect them before staging:

```bash
git diff package.json package-lock.json turbo.json docker-compose.yml
```

## Recommended First Frontend Deliverables

### 1. App Shell

Build the base authenticated application layout.

Should include:

- Top navigation.
- Sidebar or compact project navigation.
- Main content area.
- Loading state.
- Empty state.
- Error state.
- Responsive mobile layout.

Suggested screens:

```text
/                 -> redirect or landing/dashboard placeholder
/dashboard        -> repository overview
/repositories     -> imported repositories
/repositories/:id -> repository detail placeholder
```

Do not implement AI chat yet.

### 2. Authentication UI Flow

Build frontend screens around the existing backend auth flow.

Backend endpoints available:

```http
GET /api/v1/auth/github/login
GET /api/v1/auth/github/callback
GET /api/v1/auth/me
```

Expected frontend behavior:

1. User clicks `Continue with GitHub`.
2. Frontend calls `/api/v1/auth/github/login`.
3. Frontend redirects browser to `authorization_url`.
4. GitHub redirects to backend callback.
5. Backend returns a CodeDNA JWT.
6. Frontend stores the CodeDNA JWT locally.
7. Frontend uses the JWT for future API calls.

Important:

- The frontend should never store or display the GitHub access token.
- The frontend authenticates only with the CodeDNA JWT.

For the MVP, storing the CodeDNA JWT in browser storage is acceptable for local testing.
Before production, token storage should be reviewed.

### 3. Repository Discovery UI

Build a page that lists GitHub repositories accessible to the authenticated user.

Backend endpoint:

```http
GET /api/v1/github/repositories?visibility=all&sort=updated&page=1&per_page=30
```

UI should show:

- Repository name.
- Owner/name.
- Visibility.
- Default branch.
- Import button.
- Pagination controls.
- Loading/error/empty states.

Do not let the frontend send trusted repository metadata during import.

### 4. Repository Import UI

Use the existing backend import endpoint:

```http
POST /api/v1/repositories
```

Allowed request body:

```json
{
  "full_name": "owner/repository"
}
```

or:

```json
{
  "github_id": "123456789"
}
```

Do not send:

```json
{
  "clone_url": "...",
  "default_branch": "...",
  "visibility": "...",
  "status": "..."
}
```

Reason:

The backend must fetch canonical metadata from GitHub. Frontend-supplied metadata is not trusted.

### 5. Imported Repository List

Backend endpoint:

```http
GET /api/v1/repositories
```

UI should show:

- Imported repository name.
- Status.
- Last cloned time.
- Last indexed time when available.
- Button to start indexing.
- Link to repository detail screen.

Repository statuses currently include:

```text
registered
indexing
ready
failed
cloning
archived
```

Only `registered`, `cloning`, `ready`, and `failed` are expected right now.

### 6. Indexing Job UI

Backend endpoint to start indexing:

```http
POST /api/v1/repositories/{repository_id}/index
```

Expected response:

```json
{
  "repository_id": "2353ab83-0db6-49e4-8503-83fd1fc0bfef",
  "job_id": "87bfc7b3-278d-4385-a5cf-80656e0065e9",
  "status": "queued"
}
```

Then poll:

```http
GET /api/v1/jobs/{job_id}
```

Job statuses:

```text
queued
running
completed
failed
```

UI should show:

- Queued state.
- Running state.
- Completed state.
- Failed state with error message.

Important:

Use the `job_id` returned by the index endpoint. Do not use a placeholder UUID from Swagger.

## Frontend API Client Boundary

Create a small frontend API client instead of scattering `fetch` calls everywhere.

Suggested file:

```text
apps/web/lib/api.ts
```

Suggested responsibilities:

- Store the base API URL.
- Attach the CodeDNA JWT to requests.
- Parse JSON responses.
- Handle common API errors.

The API base URL should come from:

```text
NEXT_PUBLIC_API_URL
```

Local value:

```text
http://localhost:8001
```

Do not hardcode the backend URL inside components.

## Frontend Type Boundaries

Create frontend types that mirror backend responses.

Suggested file:

```text
apps/web/types/api.ts
```

Useful types:

```ts
export type RepositoryStatus =
  | "registered"
  | "cloning"
  | "indexing"
  | "ready"
  | "failed"
  | "archived";

export type JobStatus = "queued" | "running" | "completed" | "failed";
```

Keep these types aligned with `docs/API.md`.

## Local Frontend Verification

Start backend:

```bash
API_PORT=8001 docker compose up -d --build api postgres redis worker
docker compose run --rm --build migrate
```

Start frontend:

```bash
npm install
npm run dev --workspace=web
```

Expected frontend URL:

```text
http://localhost:3000
```

If port `3000` is busy, Next.js may choose another port. Use the URL printed in the terminal.

Run checks:

```bash
npm run lint --workspace=web
npm run typecheck --workspace=web
npm run build --workspace=web
```

## Manual Product Flow to Test

The frontend teammate should verify this flow:

1. Open frontend.
2. Click `Continue with GitHub`.
3. Complete GitHub OAuth.
4. Confirm the app shows the logged-in user.
5. Open repository discovery screen.
6. See GitHub repositories.
7. Import one repository.
8. See it in imported repositories.
9. Click start indexing.
10. See job status move from `queued` or `running` to `completed`.
11. See repository status become `ready`.

## What She Should Not Build Yet

Do not build these features yet:

- Real AI chat.
- Repository file explorer backed by parsed files.
- Code search backed by embeddings.
- Graph visualization backed by graph tables.
- Commit/PR/issue timeline.
- Billing.
- Team management.
- Fine-grained authorization.

These need backend milestones that do not exist yet.

Mockups or static placeholders are fine if clearly marked as placeholders.

## How to Avoid Affecting Backend Development

Follow these rules:

- Keep frontend feature branches separate from backend branches.
- Do not stage backend files unless intentionally changing backend integration.
- Do not edit database migrations.
- Do not change API request/response contracts.
- Do not commit `.env` files or tokens.
- Do not change Docker Compose unless the frontend needs a documented environment variable.
- Keep dependency changes small and explain them in the PR.
- Prefer frontend-only files under `apps/web/`.

## PR Checklist for Frontend Work

Before opening a PR:

```bash
git status --short
npm run lint --workspace=web
npm run typecheck --workspace=web
npm run build --workspace=web
```

The PR description should include:

- What screens changed.
- What API endpoints are used.
- Any new environment variables.
- Screenshots or short screen recording.
- Known placeholders.
- Confirmation that no backend migrations or API contracts were changed.

## Suggested First PR

Recommended first frontend PR:

```text
frontend/dashboard-shell
```

Scope:

- Replace default Next starter page.
- Add CodeDNA app shell.
- Add login button.
- Add placeholder dashboard.
- Add repository list placeholder.
- Add frontend API client skeleton.
- Add frontend types for current backend responses.

Avoid:

- Full AI chat.
- Graph UI.
- Large dependency changes.
- Backend code changes.

This PR gives the frontend a foundation without colliding with backend indexing work.
