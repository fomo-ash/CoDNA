from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.repositories.dependencies import get_repository_service
from app.modules.repositories.interfaces import RepositoryService
from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead


router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryRead], status_code=status.HTTP_200_OK)
async def list_repositories(
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
) -> list[RepositoryRead]:
    try:
        return list(await service.list_repositories(session))
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_repository(
    payload: RepositoryCreate,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryRead:
    try:
        return await service.create_repository(session, payload)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc


@router.get("/{repository_id}", response_model=RepositoryRead, status_code=status.HTTP_200_OK)
async def get_repository(
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryRead:
    try:
        return await service.get_repository(session, repository_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
