# CodeDNA Architecture

> **Version:** 1.0.0
> **Project:** CodeDNA
> **Status:** Design Phase
> **Authors:** Team CodeDNA

---

# Vision

CodeDNA is an AI-powered software intelligence platform that decodes the "DNA" of any software project.

Instead of searching through thousands of files, developers can ask questions in natural language and receive answers backed by source code, commit history, pull requests, issues, documentation, and architectural context.

The goal is not to generate code.

The goal is to understand software.

---

# Problem Statement

Modern software projects grow rapidly.

A typical production repository contains:

- Hundreds of folders
- Thousands of files
- Years of commits
- Pull requests
- Issues
- Documentation
- Multiple contributors

Understanding why a system exists is often more difficult than understanding how it works.

Current AI coding assistants primarily answer questions using source code alone.

They generally ignore:

- Architectural evolution
- Commit history
- Pull request discussions
- Issue context
- Dependency relationships
- Engineering decisions

CodeDNA bridges this gap.

---

# Goals

Primary Goals

- Understand any GitHub repository.
- Explain software architecture.
- Answer repository-specific questions.
- Generate onboarding documentation.
- Build repository knowledge graphs.
- Perform semantic code search.
- Explain engineering decisions.
- Predict impact of code changes.

Secondary Goals

- Architecture visualization
- Dependency analysis
- Commit reasoning
- Contributor insights
- Timeline reconstruction

---

# Non Goals

CodeDNA is NOT

- another IDE
- another code editor
- another autocomplete assistant
- another GitHub clone

It focuses exclusively on software understanding.

---

# High Level Architecture

                    Browser
                       │
               Next.js Frontend
                       │
                REST API Gateway
                       │
        ┌──────────────┼──────────────┐
        │              │              │
 Repository       Chat Service      Search
 Service
        │
        ▼
 Background Queue
        │
        ▼
 Repository Indexer
        │
        ▼
 Tree-sitter Parser
        │
        ▼
 Semantic Chunker
        │
        ▼
 Embedding Service
        │
        ▼
 PostgreSQL + pgvector
        │
        ▼
 Knowledge Graph
        │
        ▼
 AI Orchestrator
        │
        ▼
 GPT-5

---

# Core Components

## Frontend

Responsibilities

- Authentication
- Dashboard
- Repository Explorer
- AI Chat
- Architecture Graph
- Timeline
- Settings

Technology

- Next.js
- React
- Tailwind
- shadcn/ui
- React Flow

---

## API Gateway

Responsibilities

- Authentication
- Authorization
- Validation
- Rate Limiting
- Request Routing

The gateway never performs AI tasks.

It forwards requests to the appropriate services.

---

## Repository Service

Responsibilities

- Connect GitHub
- Clone repositories
- Validate URLs
- Store metadata
- Schedule indexing

Endpoints

POST /repositories

GET /repositories

DELETE /repositories/{id}

POST /repositories/{id}/index

---

## Background Workers

Heavy operations never block the frontend.

Examples

- clone repository
- parse repository
- generate embeddings
- build graph
- refresh repository

Queue

Redis

Workers

BullMQ (Node)

or

Celery (Python)

---

## Parser

CodeDNA uses Tree-sitter.

Responsibilities

- Parse AST
- Extract classes
- Extract methods
- Extract imports
- Extract interfaces
- Extract documentation

This produces structured code rather than raw text.

---

## Semantic Chunker

Instead of fixed token chunking,

the parser creates semantic chunks.

Examples

AuthenticationService

↓

Login()

↓

JWT Generation

↓

Middleware

Each chunk becomes independently searchable.

---

## Embedding Service

Responsibilities

- Generate embeddings
- Store vectors
- Refresh embeddings
- Batch processing

Current Model

OpenAI text-embedding-3-large

Future

Support local models.

---

## Search Service

Hybrid Search

Combines

- Vector Search
- BM25
- Metadata Filtering

Pipeline

Query

↓

Embedding

↓

Vector Search

↓

Keyword Search

↓

Merge

↓

Rerank

↓

Return Context

---

## Knowledge Graph

Purpose

Represent software relationships.

Nodes

Repository

Folder

File

Class

Function

Commit

Issue

PR

Edges

Imports

Calls

Depends On

Modified By

Introduced In

Discussed In

---

## AI Orchestrator

The orchestrator coordinates reasoning.

Rather than asking GPT one huge prompt,

multiple agents collaborate.

Planner

↓

Retriever

↓

Architecture Agent

↓

Commit Agent

↓

Issue Agent

↓

Documentation Agent

↓

Answer Composer

This architecture is implemented using LangGraph.

---

# Repository Indexing Pipeline

Step 1

User submits GitHub URL

↓

Step 2

Repository metadata validation

↓

Step 3

Clone repository

↓

Step 4

Tree-sitter parsing

↓

Step 5

AST generation

↓

Step 6

Semantic chunking

↓

Step 7

Embedding generation

↓

Step 8

Commit indexing

↓

Step 9

Issue indexing

↓

Step 10

Pull Request indexing

↓

Step 11

Knowledge graph generation

↓

Repository Ready

---

# Query Pipeline

User Question

↓

Intent Detection

↓

Repository Retrieval

↓

Hybrid Search

↓

Context Compression

↓

Graph Lookup

↓

Prompt Construction

↓

GPT-5

↓

Answer with citations

---

# AI Strategy

CodeDNA follows Retrieval-Augmented Generation.

The LLM never receives the entire repository.

Instead,

only relevant repository context is retrieved.

Advantages

- Lower cost
- Better accuracy
- Lower hallucination rate
- Faster responses

---

# Data Storage

Primary Database

PostgreSQL

Stores

Users

Repositories

Metadata

Chats

Messages

Commits

Issues

PRs

---

Vector Storage

pgvector

Stores

Embeddings

---

Cache

Redis

Stores

Sessions

Rate Limits

Frequently Used Searches

Repository Status

---

Knowledge Graph

Neo4j (Future)

MVP

Stored relationally.

---

# Security

Authentication

GitHub OAuth

Authorization

JWT

Repository Validation

Repository Size Limits

Prompt Injection Protection

Rate Limiting

Input Validation

---

# Performance Strategy

Repository indexing

Background processing

Caching

Redis

Streaming responses

Server Sent Events

Parallel embedding generation

Batch indexing

---

# Scalability

Stateless API

Horizontally scalable workers

Independent embedding service

Independent AI orchestration

Containerized deployment

---

# Failure Handling

GitHub unavailable

Retry

OpenAI timeout

Retry

Embedding failure

Skip chunk

Continue indexing

Worker crash

Resume job

Repository parsing failure

Log file

Continue remaining files

---

# Observability

Structured Logging

OpenTelemetry

Metrics

Tracing

Health Endpoints

Worker Monitoring

---

# Deployment

Next.js

↓

FastAPI

↓

Redis

↓

PostgreSQL

↓

pgvector

↓

Workers

↓

Docker Compose

Production

↓

Kubernetes

---

# Future Roadmap

Phase 1

Repository Understanding

Phase 2

Knowledge Graph

Phase 3

Architecture Generation

Phase 4

Impact Prediction

Phase 5

Multi Repository Intelligence

Phase 6

Enterprise Integrations

---

# Architecture Principles

- API-first
- Event-driven indexing
- Background processing
- AI-assisted reasoning
- Stateless services
- Modular design
- Strong typing
- Horizontal scalability
- Security by default
- Retrieval before generation

---

# Summary

CodeDNA is designed as a modular AI software intelligence platform rather than a traditional chatbot.

Its architecture separates repository ingestion, semantic indexing, retrieval, reasoning, and presentation into independent services, enabling scalable repository understanding while keeping AI grounded in verifiable project context.