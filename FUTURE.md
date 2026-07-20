# CodeDNA: Future Roadmap

CodeDNA is designed to grow from a local repository-intelligence tool into a reliable, publicly available platform for understanding and working with codebases. The next phase focuses on accessibility, accuracy, security, and deeper AI-powered workflows.

## 1. Public Deployment

We plan to make CodeDNA available through a production deployment so users can access it without local setup.

- Deploy the web application, API, and background worker as managed production services.
- Use PostgreSQL with pgvector for application data and semantic search, Redis for job coordination, and durable storage for repository workspaces.
- Configure production GitHub OAuth, HTTPS, restricted CORS origins, monitoring, backups, and error reporting.
- Introduce sensible repository-size, indexing, retention, and usage limits to keep the service dependable as it grows.
- Provide a staging environment to validate releases before they reach users.

## 2. Becoming Part of the OpenAI Ecosystem

We intend to deepen CodeDNA's use of OpenAI capabilities where they genuinely improve the developer experience.

- Use OpenAI models for higher-quality repository Q&A, summaries, change explanations, and guided codebase exploration.
- Use embeddings to improve semantic and hybrid search across files, symbols, documentation, commits, pull requests, and issues.
- Surface grounded answers with citations to the relevant repository files and context.
- Keep provider credentials secure on the server and make model-backed features transparent about availability and usage.
- Explore OpenAI ecosystem integrations that make CodeDNA easier to use in real engineering workflows, while preserving a useful lexical-search path when AI features are unavailable.

## 3. More Accurate and Trustworthy Results

Accuracy is the most important requirement for a tool that explains code.

- Add evaluation fixtures for factuality, citation coverage, relevance, and rejection of unsupported answers.
- Improve code parsing, symbol detection, dependency mapping, and chunking so retrieved context is more precise.
- Add confidence signals and clear source links so users can verify answers quickly.
- Strengthen retrieval with file-, path-, and symbol-aware search, along with better ranking and filtering.
- Test answers against known repositories and regression cases before shipping model or retrieval changes.

## 4. Private Repository Support

Private repositories are a major next step for teams that need repository intelligence on their own work.

- Support GitHub-authorized access to private repositories with explicit user consent.
- Enforce repository ownership checks and strict isolation between users and organizations.
- Keep GitHub tokens, provider keys, and session credentials server-side and out of the browser.
- Add clear controls for repository deletion, data retention, re-indexing, and export.
- Provide audit logs, rate limits, quotas, and per-user spending safeguards for production use.

## 5. A Richer Repository View

We will continue making CodeDNA more useful beyond a single question-and-answer interaction.

- Add per-file and symbol-level history, including when code was introduced or changed.
- Connect commits, pull requests, issues, changed files, and code chunks into a navigable engineering timeline.
- Improve impact analysis so developers can see which files and symbols may be affected by a change.
- Add clearer indexing status, retry controls, and graceful lexical-only behavior when semantic features are not configured.
- Refine the frontend with stronger navigation, understandable loading and error states, and a more focused workflow for exploring large repositories.

## 6. Production Readiness

Before broad release, we will validate CodeDNA across the full user journey.

- Test sign-in, public and private imports, indexing, history ingestion, search, Q&A, citations, and failure recovery.
- Run worker and API integration tests for background processing, provider failures, and access-control boundaries.
- Add browser-level end-to-end tests for the most important user flows.
- Monitor performance, cost, and reliability under realistic repository sizes and usage patterns.

## Goal

The goal is to deliver a secure, accurate, and accessible code-intelligence platform that helps developers understand unfamiliar repositories faster. CodeDNA will combine dependable engineering foundations with carefully applied OpenAI capabilities, while keeping user trust, privacy, and verifiable answers at the center of the product.
