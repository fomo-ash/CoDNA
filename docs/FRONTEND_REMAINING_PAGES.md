# Frontend Remaining Pages Handoff

## Scope

Build the remaining CodeDNA user interface while backend work continues. Use mock
fixtures where needed, but keep API calls behind `apps/web/lib/api.ts` so they can
be enabled during the later integration pass.

Do not modify `apps/api/`, Alembic migrations, Docker Compose, root package files,
or backend API contracts without coordination.

## Current Screens

| Route | State | Required work |
| --- | --- | --- |
| `/` | Landing page exists | Keep as product landing page; replace mock-only login actions with a clear auth entry point. |
| `/dashboard` | Mock dashboard exists | Finalize layout, loading, empty, error, and indexing-status states. |
| `/repositories/[id]` | Initial detail page exists | Replace with the repository explorer described below. |

## Pages to Build

### 1. GitHub Authentication Callback

**Route:** `/auth/callback`

- Handle successful and failed CodeDNA OAuth redirects.
- Extract only the CodeDNA JWT supplied by the backend; never expose or store a GitHub token.
- Show loading, success, expired/invalid-token, and retry states.
- Redirect successful users to `/dashboard`.

### 2. Repository Dashboard

**Route:** `/dashboard`

- Imported repository list with name, visibility, branch, status, last indexed time, and action menu.
- Empty state with an "Import repository" action.
- Indexing progress state: queued, cloning, indexing, ready, failed.
- Failed-job panel with safe error summary and retry button.
- Responsive table-to-card behavior on small screens.

### 3. GitHub Repository Import

**Route:** `/repositories/import` (or dashboard modal/drawer)

- Searchable, paginated list of GitHub repositories.
- Visibility filter: all, public, private.
- Import action with pending, success, duplicate, and failure states.
- Never request clone URLs or repository metadata from the user; the backend remains authoritative.

### 4. Repository Explorer

**Route:** `/repositories/[id]`

Build a persistent repository header (name, branch, indexing status, last indexed
time) and these tabs:

| Tab | Main content | Backend endpoint available at integration |
| --- | --- | --- |
| Overview | Stats, language distribution, recent index status | `GET /repositories/{id}/stats` |
| Files | Filterable inventory table | `GET /repositories/{id}/files` |
| Parse results | Parse status, language, symbols/import counts | `GET /repositories/{id}/parse-results` |
| Knowledge | Extracted symbols, docs, config, schema facts | `GET /repositories/{id}/knowledge` |
| Chunks | Content, metadata, relationships, path and line ranges | `GET /repositories/{id}/chunks` |

For a selected chunk, show:

- Chunk type, source type, title, path, language, and line range.
- Source content in a readable code/document panel.
- Relationship groups: calls, called by, imports, imported by, references, exports, inheritance, and unresolved facts.
- Stable chunk ID with copy action.

### 5. Search Results

**Route:** `/repositories/[id]/search`

- Query input, source-type filter, chunk-type filter, and result limit control.
- Results show title, path, line range, chunk type, source type, and relevance score.
- Result click opens the matching chunk in the explorer.
- Empty, no-match, loading, and provider-unavailable states.
- This is retrieval only: do not add answer/chat generation yet.

### 6. Shared UI States and Components

Create reusable frontend components for:

- `AppShell`, navigation, repository header, status badge, pagination, filters.
- Loading skeletons, empty states, error notices, retry button, copy button.
- Source/code viewer with line-range label.
- Chunk relationship list and citation/path link.

## Design Requirements

- Citation-first UI: paths, line ranges, and chunk IDs must be visible wherever repository facts are shown.
- Never display provider API keys, GitHub access tokens, or raw backend stack traces.
- Preserve owner-scoped assumptions; no UI control should imply cross-user repository access.
- Build responsive layouts and keyboard-accessible controls.
- Keep mock fixture data isolated under `apps/web/lib/fixtures/` or equivalent; do not hardcode it inside page components.

## Integration Boundary (Do Later)

The existing frontend currently runs in mock mode. Do not block page work on live
integration. During the integration pass, backend ownership will:

1. Disable mock mode through environment configuration.
2. Connect the API client to `NEXT_PUBLIC_API_URL`.
3. Wire GitHub OAuth and CodeDNA JWT storage.
4. Replace fixtures with the endpoints listed above.
5. Add browser-level integration tests for import, indexing, explorer, and search.

## Definition of Done

- Every listed route renders with fixtures and has loading, empty, and error states.
- Types are explicit; no `any` for API-facing state.
- `npm run lint --workspace web` and `npm run typecheck --workspace web` pass.
- No changes outside `apps/web/` and this handoff document unless agreed first.
