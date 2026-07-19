from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.repositories.service import RepositoryNotFoundError
from app.modules.retrieval.dependencies import get_repository_retrieval_service
from app.modules.retrieval.schemas import RepositorySearchResponse
from app.modules.retrieval.service import RepositoryRetrievalService


router = APIRouter(prefix="/repositories", tags=["repository-retrieval"])


@router.get("/{repository_id}/search", response_model=RepositorySearchResponse)
async def search_repository(
    repository_id: UUID,
    query: str = Query(..., min_length=1, max_length=1000),
    source_type: str | None = Query(None, min_length=1, max_length=64),
    chunk_type: str | None = Query(None, min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryRetrievalService = Depends(get_repository_retrieval_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositorySearchResponse:
    try:
        return await service.search(
            session, repository_id, current_user.id, query, source_type, chunk_type, limit
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc
