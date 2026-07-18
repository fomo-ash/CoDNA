from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.files.dependencies import get_repository_file_service
from app.modules.files.interfaces import RepositoryFileService
from app.modules.files.schemas import RepositoryFileListResponse, RepositoryStatsRead
from app.modules.repositories.service import RepositoryNotFoundError


router = APIRouter(prefix="/repositories", tags=["repository-files"])


@router.get(
    "/{repository_id}/files",
    response_model=RepositoryFileListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_repository_files(
    repository_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    language: str | None = Query(None, min_length=1),
    extension: str | None = Query(None, min_length=1),
    path_prefix: str | None = Query(None, min_length=1),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryFileService = Depends(get_repository_file_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryFileListResponse:
    try:
        return await service.list_repository_files(
            session,
            repository_id,
            current_user.id,
            page,
            page_size,
            language,
            extension,
            path_prefix,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc


@router.get(
    "/{repository_id}/stats",
    response_model=RepositoryStatsRead,
    status_code=status.HTTP_200_OK,
)
async def get_repository_stats(
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryFileService = Depends(get_repository_file_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryStatsRead:
    try:
        return await service.get_repository_stats(session, repository_id, current_user.id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc
