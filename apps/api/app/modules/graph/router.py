from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.graph.dependencies import get_repository_graph_service
from app.modules.graph.schemas import (
    RepositoryGraphResponse,
    RepositoryImpactResponse,
    RepositoryImpactTraversalResponse,
    RepositorySymbolImpactTraversalResponse,
)
from app.modules.graph.service import RepositoryGraphService
from app.modules.repositories.service import RepositoryNotFoundError

router = APIRouter(prefix="/repositories", tags=["repository-graph"])


@router.get("/{repository_id}/graph", response_model=RepositoryGraphResponse)
async def repository_graph(repository_id: UUID, limit: int = Query(500, ge=1, le=2000), session: AsyncSession = Depends(get_db_session), service: RepositoryGraphService = Depends(get_repository_graph_service), current_user: User = Depends(get_current_user_record)) -> RepositoryGraphResponse:
    try:
        return await service.graph(session, repository_id, current_user.id, limit)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc


@router.get("/{repository_id}/impact/traverse", response_model=RepositoryImpactTraversalResponse)
async def traverse_repository_impact(repository_id: UUID, path: str = Query(..., min_length=1, max_length=2048), depth: int = Query(2, ge=1, le=3), session: AsyncSession = Depends(get_db_session), service: RepositoryGraphService = Depends(get_repository_graph_service), current_user: User = Depends(get_current_user_record)) -> RepositoryImpactTraversalResponse:
    try:
        return await service.traverse_impact(session, repository_id, current_user.id, path, depth)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc


@router.get("/{repository_id}/impact/symbol", response_model=RepositorySymbolImpactTraversalResponse)
async def traverse_symbol_impact(
    repository_id: UUID,
    stable_symbol_id: str = Query(..., min_length=1, max_length=4096),
    depth: int = Query(2, ge=1, le=3),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryGraphService = Depends(get_repository_graph_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositorySymbolImpactTraversalResponse:
    try:
        return await service.traverse_symbol_impact(session, repository_id, current_user.id, stable_symbol_id, depth)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc


@router.get("/{repository_id}/impact", response_model=RepositoryImpactResponse)
async def repository_impact(repository_id: UUID, path: str = Query(..., min_length=1, max_length=2048), limit: int = Query(200, ge=1, le=1000), include_unresolved: bool = False, include_tests: bool = False, include_internal: bool = False, session: AsyncSession = Depends(get_db_session), service: RepositoryGraphService = Depends(get_repository_graph_service), current_user: User = Depends(get_current_user_record)) -> RepositoryImpactResponse:
    try:
        return await service.impact(session, repository_id, current_user.id, path, limit, include_unresolved, include_tests, include_internal)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc
