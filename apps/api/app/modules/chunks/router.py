from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.chunks.dependencies import get_repository_chunk_service
from app.modules.chunks.schemas import RepositoryChunkListResponse, RepositoryChunkRead
from app.modules.chunks.service import RepositoryChunkNotFoundError, RepositoryChunkServiceImpl
from app.modules.repositories.service import RepositoryNotFoundError


repository_router = APIRouter(prefix="/repositories", tags=["repository-chunks"])
chunk_router = APIRouter(prefix="/chunks", tags=["repository-chunks"])


@repository_router.get("/{repository_id}/chunks", response_model=RepositoryChunkListResponse)
async def list_repository_chunks(
    repository_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    source_type: str | None = Query(None, min_length=1),
    chunk_type: str | None = Query(None, min_length=1),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryChunkServiceImpl = Depends(get_repository_chunk_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryChunkListResponse:
    try:
        return await service.list_repository_chunks(
            session, repository_id, current_user.id, page, page_size, source_type, chunk_type
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc


@chunk_router.get("/{chunk_id}", response_model=RepositoryChunkRead)
async def get_chunk(
    chunk_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryChunkServiceImpl = Depends(get_repository_chunk_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryChunkRead:
    try:
        return await service.get_chunk(session, chunk_id, current_user.id)
    except RepositoryChunkNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found.") from exc
