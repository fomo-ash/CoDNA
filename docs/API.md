# CodeDNA API

## Base URL

Local development uses `http://localhost:8001` when the API is started with `API_PORT=8001`. The default Compose port is `8000`.

All application routes are under `/api/v1`.

For a full manual verification sequence with beginner explanations, see [Backend Verification Guide](BACKEND_VERIFICATION_GUIDE.md).

For repository inventory implementation details and troubleshooting, see [Repository Inventory and File Discovery](REPOSITORY_INVENTORY.md).

## Authentication

Start GitHub OAuth:

```http
GET /api/v1/auth/github/login
```

After GitHub approval, the callback returns a CodeDNA JWT. Use it as:

```http
Authorization: Bearer <codedna-jwt>
```

The GitHub access token is retained by the backend and is never included in CodeDNA responses.

## GitHub Discovery

### Current GitHub profile

```http
GET /api/v1/github/me
```

Example response:

```json
{
  "github_id": "12345",
  "username": "octocat",
  "email": "octocat@example.com",
  "name": "The Octocat",
  "avatar_url": "https://avatars.example.com/u/12345"
}
```

### List accessible repositories

```http
GET /api/v1/github/repositories?visibility=all&sort=updated&page=1&per_page=30
```

Query parameters:

| Parameter | Values | Default |
| --- | --- | --- |
| `visibility` | `all`, `public`, `private` | `all` |
| `sort` | `created`, `updated`, `pushed`, `full_name` | `updated` |
| `page` | Positive integer | `1` |
| `per_page` | `1` to `100` | `30` |

Example response:

```json
{
  "repositories": [
    {
      "github_id": "12345",
      "name": "example",
      "full_name": "octo/example",
      "default_branch": "main",
      "clone_url": "https://github.com/octo/example.git",
      "visibility": "private",
      "private": true
    }
  ],
  "page": 1,
  "per_page": 30,
  "has_next_page": false
}
```

## Repository Import

### Import by GitHub ID

```http
POST /api/v1/repositories
Content-Type: application/json
```

```json
{
  "github_id": "12345"
}
```

### Import by full name

```json
{
  "full_name": "octo/example"
}
```

Exactly one identifier is required. The client must not send `clone_url`, `default_branch`, `visibility`, `status`, or `owner_id`; those values are fetched or assigned by the backend.

Successful response: `201 Created` with the persisted repository record. The initial status is `registered`.

### List imported repositories

```http
GET /api/v1/repositories
```

### Read an imported repository

```http
GET /api/v1/repositories/{repository_id}
```

Repository list and detail responses are always scoped to the authenticated CodeDNA user.

### Start repository indexing

```http
POST /api/v1/repositories/{repository_id}/index
```

This creates a durable job record, enqueues a Celery task through Redis, and returns immediately.
The current task shallow-clones the repository into the worker workspace, discovers source file metadata, parses supported source files with Tree-sitter, extracts structured repository knowledge, records clone/index metadata, and completes successfully.
It does not generate embeddings, build a graph, or call AI yet.

Example response:

```json
{
  "repository_id": "00000000-0000-0000-0000-000000000002",
  "job_id": "00000000-0000-0000-0000-000000000003",
  "status": "queued"
}
```

If the repository already has a queued or running index job, the API returns that existing job instead of enqueueing a duplicate.

### List discovered repository files

```http
GET /api/v1/repositories/{repository_id}/files?page=1&page_size=100
```

This returns file metadata discovered by the background indexing job. The endpoint is scoped to the authenticated owner and does not expose local clone paths or file contents.

Query parameters:

| Parameter | Description | Default |
| --- | --- | --- |
| `page` | Positive page number | `1` |
| `page_size` | `1` to `500` files per page | `100` |
| `language` | Optional exact detected language filter | none |
| `extension` | Optional extension filter, with or without `.` | none |
| `path_prefix` | Optional repository-relative path prefix filter | none |

Example response:

```json
{
  "files": [
    {
      "id": "00000000-0000-0000-0000-000000000004",
      "repository_id": "00000000-0000-0000-0000-000000000002",
      "path": "src/app.py",
      "filename": "app.py",
      "extension": "py",
      "language": "Python",
      "size_bytes": 1234,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "is_binary": false,
      "discovered_at": "2026-07-18T00:00:00Z",
      "created_at": "2026-07-18T00:00:00Z",
      "updated_at": "2026-07-18T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "has_next_page": false
}
```

Known binary asset extensions, files larger than 10 MB, secret-like env files, dependency directories, build output, editor directories, and VCS directories are skipped during discovery. Other binary files are inventoried with `is_binary=true` and no detected source language.

### List repository parse results

```http
GET /api/v1/repositories/{repository_id}/parse-results?page=1&page_size=100
```

This returns Tree-sitter parse metadata from the latest successful indexing job. Parse results are scoped to the authenticated owner.

Query parameters:

| Parameter | Description | Default |
| --- | --- | --- |
| `page` | Positive page number | `1` |
| `page_size` | `1` to `500` parse results per page | `100` |
| `status` | Optional exact parse status filter | none |
| `language` | Optional exact detected language filter | none |
| `path_prefix` | Optional repository-relative path prefix filter | none |

Supported parse statuses:

| Status | Meaning |
| --- | --- |
| `parsed` | File parsed without Tree-sitter syntax errors |
| `syntax_error` | Tree-sitter parsed the file but reported syntax errors |
| `unsupported` | File is text but no grammar is configured yet |
| `skipped` | File is binary and intentionally not parsed |
| `failed` | Parser failed to read or parse the file |

Example response:

```json
{
  "parse_results": [
    {
      "id": "00000000-0000-0000-0000-000000000005",
      "repository_id": "00000000-0000-0000-0000-000000000002",
      "repository_file_id": "00000000-0000-0000-0000-000000000004",
      "path": "src/app.py",
      "language": "Python",
      "parser": "python",
      "status": "parsed",
      "root_node_type": "module",
      "has_error": false,
      "error_count": 0,
      "symbol_count": 1,
      "import_count": 1,
      "symbols": [
        {
          "name": "build",
          "kind": "function",
          "start_line": 3,
          "end_line": 4
        }
      ],
      "imports": [
        {
          "statement": "import os",
          "start_line": 1,
          "end_line": 1
        }
      ],
      "parsed_at": "2026-07-18T00:00:00Z",
      "error_message": null,
      "created_at": "2026-07-18T00:00:00Z",
      "updated_at": "2026-07-18T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "has_next_page": false
}
```

Current Tree-sitter support covers Python, JavaScript, TypeScript, and TSX. Unsupported text files still get a persisted status so the parser stage is auditable.

### List repository knowledge items

```http
GET /api/v1/repositories/{repository_id}/knowledge?page=1&page_size=100
```

This returns structured knowledge extracted after inventory and parsing. The endpoint is scoped to the authenticated owner.

Query parameters:

| Parameter | Description | Default |
| --- | --- | --- |
| `page` | Positive page number | `1` |
| `page_size` | `1` to `500` knowledge items per page | `100` |
| `source_type` | Optional source filter: `source_code`, `documentation`, `database_schema`, or `configuration` | none |
| `item_type` | Optional exact item type filter | none |
| `path_prefix` | Optional repository-relative path prefix filter | none |

Current extractors:

| Source type | Extracted item types |
| --- | --- |
| `source_code` | `source_file`, `symbol`, `import` |
| `documentation` | `document`, `document_section` |
| `database_schema` | `prisma_schema`, `prisma_model`, `prisma_enum` |
| `configuration` | `package_manifest`, `python_project`, `python_requirements`, `typescript_config`, `dockerfile`, `compose_config` |

Example response:

```json
{
  "knowledge_items": [
    {
      "id": "00000000-0000-0000-0000-000000000006",
      "repository_id": "00000000-0000-0000-0000-000000000002",
      "repository_file_id": "00000000-0000-0000-0000-000000000004",
      "path": "README.md",
      "source_type": "documentation",
      "item_type": "document",
      "name": "Project Guide",
      "extractor": "documentation",
      "data": {
        "title": "Project Guide",
        "heading_count": 4,
        "link_count": 2,
        "code_block_count": 1
      },
      "extracted_at": "2026-07-18T00:00:00Z",
      "created_at": "2026-07-18T00:00:00Z",
      "updated_at": "2026-07-18T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 100,
  "has_next_page": false
}
```

This knowledge layer intentionally stops before embeddings, vector search, graph generation, and AI orchestration.

### Read repository inventory statistics

```http
GET /api/v1/repositories/{repository_id}/stats
```

This returns the persisted statistics from the latest successful inventory scan.

Example response:

```json
{
  "repository_id": "00000000-0000-0000-0000-000000000002",
  "total_files": 1483,
  "source_files": 1094,
  "binary_files": 82,
  "total_size_bytes": 18734562,
  "languages": {
    "Python": 512,
    "TypeScript": 274,
    "Markdown": 36
  },
  "last_scan_at": "2026-07-18T00:00:00Z"
}
```

## Jobs

### Read job status

```http
GET /api/v1/jobs/{job_id}
```

Job responses are scoped through repository ownership, so one user cannot read another user's job.

## Health

```http
GET /api/v1/health
GET /api/v1/live
GET /api/v1/ready
```

## Error Responses

| Status | Meaning |
| --- | --- |
| `401` | Missing/invalid CodeDNA JWT or missing GitHub authorization |
| `404` | GitHub repository is not found/inaccessible, or local repository is not owned by the caller |
| `409` | The caller already imported the GitHub repository |
| `422` | Invalid query parameters or import payload |
| `502` | GitHub API failure |
| `503` | Indexing task could not be enqueued |

Embeddings, graph generation, and AI orchestration are intentionally outside this milestone.
