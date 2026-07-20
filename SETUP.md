# CoDNA end-to-end setup

This guide takes a new contributor from a fresh clone to a working local CoDNA
environment: sign in with GitHub, import a repository, wait for indexing, and
ask a cited question.

## What you need

- Git and Docker Desktop with Docker Compose v2 running.
- A GitHub OAuth app (needed for sign-in and repository discovery).
- An OpenAI API key for the default embedding and answer providers, or a Google API key when using the supported Gemini alternative.

The Docker setup installs Node and Python dependencies inside containers, so
Node.js and Python are not required on the host.

## 1. Clone and create local configuration

```bash
git clone <your-fork-or-repository-url> CoDNA
cd CoDNA
cp .env.example .env
cp apps/api/.env.example apps/api/.env
```

The root `.env` controls browser-facing ports and API URL. Keep these local
defaults unless another process already uses them:

```dotenv
API_PORT=8001
WEB_PORT=3333
NEXT_PUBLIC_API_URL=http://localhost:8001
```

`NEXT_PUBLIC_API_URL` is compiled into the frontend during its Docker build.
If you change it, rebuild the `web` service; restarting the container alone is
not enough.

## 2. Configure GitHub OAuth

1. In GitHub, open **Settings → Developer settings → OAuth Apps → New OAuth
   App**.
2. Set the application home page to `http://localhost:3333`.
3. Set the authorization callback URL to
   `http://localhost:3333/auth/callback`.
4. Copy the client ID and generate a client secret.

Edit `apps/api/.env` and replace the placeholder values. At minimum set:

```dotenv
OPENAI_API_KEY=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_CALLBACK_URL=http://localhost:3333/auth/callback
FRONTEND_URL=http://localhost:3333
JWT_SECRET=replace-with-a-long-random-secret
```

Keep `apps/api/.env` private. It is ignored by Git. A suitable `JWT_SECRET`
can be generated with `openssl rand -hex 32`.

The default provider configuration uses OpenAI for both embeddings and answers:

```dotenv
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
ANSWER_PROVIDER=openai
ANSWER_MODEL=gpt-5.4-mini
```

Gemini remains supported as an alternative: set
`EMBEDDING_PROVIDER=google`, `EMBEDDING_MODEL=gemini-embedding-001`, and add
`GOOGLE_API_KEY`. If either provider setting changes, make sure the
corresponding API key is present. The configured embedding dimensions must stay
at `1536` because the database vector index uses that dimension.

## 3. Start the full stack

From the repository root, build the images, apply migrations, and start all
long-running services:

```bash
docker compose build
docker compose run --rm migrate
docker compose up -d
```

Check that every long-running service is up:

```bash
docker compose ps
curl http://localhost:8001/api/v1/health
```

Expected services are `postgres`, `redis`, `api`, `worker`, and `web`. Open
`http://localhost:3333` once the API health request succeeds.

For a single command on later runs, use:

```bash
docker compose up -d --build
```

## 4. Verify the product flow

1. Open `http://localhost:3333` and choose **Continue with GitHub**.
2. Authorize the OAuth app. You should return to CoDNA signed in.
3. Open the repositories area and import a repository you are allowed to read.
4. Wait for its indexing job to finish. The worker clones the repository,
   inventories files, parses supported languages, extracts knowledge, and
   creates searchable chunks and embeddings.
5. Open that repository’s **Search** page and ask a question about the code.
6. Confirm that the answer includes citations, then use the **Files**,
   **Parse**, **Knowledge facts**, **Chunks**, and **History** views to inspect
   the underlying evidence.

If a job does not advance, view the worker logs:

```bash
docker compose logs -f worker
```

For API failures, use:

```bash
docker compose logs -f api
```

## Common fixes

| Symptom | Check |
| --- | --- |
| GitHub says the callback URL is invalid | The GitHub OAuth app and `GITHUB_CALLBACK_URL` must both use `http://localhost:3333/auth/callback`. |
| The browser cannot reach the API | Confirm `NEXT_PUBLIC_API_URL=http://localhost:8001`, then run `docker compose up -d --build web`. |
| Sign-in succeeds but the browser reports CORS | Set `FRONTEND_URL=http://localhost:3333` in `apps/api/.env`, then rebuild/restart `api`. |
| Indexing fails | Inspect worker logs. Missing embedding credentials do not block inventory, parsing, chunks, or lexical search; they only prevent vector embeddings. |
| Answers fail but search results exist | Check the key for `ANSWER_PROVIDER`—the default OpenAI answer provider needs `OPENAI_API_KEY`. |
| A port is in use | Change `API_PORT`, `WEB_PORT`, `NEXT_PUBLIC_API_URL`, `FRONTEND_URL`, and GitHub’s callback URL together, then rebuild `web` and restart the stack. |

## Stop or reset local data

Stop containers while keeping the database and indexed repositories:

```bash
docker compose down
```

To remove the local database, Redis data, and cloned/indexed repositories as
well, use this intentionally destructive command:

```bash
docker compose down -v
```

## Deployment note

For a deployed environment, replace every `localhost` value with public HTTPS
URLs, register the matching HTTPS GitHub callback URL, use a strong unique JWT
secret, and provide the public API URL as a **Docker build argument** through
`NEXT_PUBLIC_API_URL`. Do not commit either `.env` file or API keys.
