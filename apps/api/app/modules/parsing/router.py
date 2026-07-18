from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.parsing.dependencies import get_repository_parser_service
from app.modules.parsing.interfaces import RepositoryParserService
from app.modules.parsing.schemas import RepositoryFileParseListResponse
from app.modules.repositories.service import RepositoryNotFoundError


router = APIRouter(prefix="/repositories", tags=["repository-parsing"])


@router.get(
    "/{repository_id}/parse-results",
    response_model=RepositoryFileParseListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_repository_parse_results(
    repository_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    status_filter: str | None = Query(None, alias="status", min_length=1),
    language: str | None = Query(None, min_length=1),
    path_prefix: str | None = Query(None, min_length=1),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryParserService = Depends(get_repository_parser_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryFileParseListResponse:
    try:
        return await service.list_repository_parse_results(
            session,
            repository_id,
            current_user.id,
            page,
            page_size,
            status_filter,
            language,
            path_prefix,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc
