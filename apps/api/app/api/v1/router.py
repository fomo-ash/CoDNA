from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.chunks.router import chunk_router, repository_router as chunks_repository_router
from app.modules.files.router import router as files_router
from app.modules.github.router import router as github_router
from app.modules.jobs.router import router as jobs_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.parsing.router import router as parsing_router
from app.modules.repositories.router import router as repositories_router
from app.modules.retrieval.router import router as retrieval_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(github_router)
api_router.include_router(jobs_router)
api_router.include_router(repositories_router)
api_router.include_router(files_router)
api_router.include_router(parsing_router)
api_router.include_router(knowledge_router)
api_router.include_router(chunks_repository_router)
api_router.include_router(chunk_router)
api_router.include_router(retrieval_router)
