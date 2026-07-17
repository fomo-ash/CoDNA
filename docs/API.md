# CodeDNA API

## Base URL

Local development uses `http://localhost:8001` when the API is started with `API_PORT=8001`. The default Compose port is `8000`.

All application routes are under `/api/v1`.

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

Repository cloning, background jobs, indexing, embeddings, graph generation, and AI orchestration are intentionally outside this milestone.
