from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.knowledge.dependencies import get_repository_knowledge_service
from app.modules.knowledge.interfaces import RepositoryKnowledgeService
from app.modules.knowledge.schemas import RepositoryKnowledgeItemListResponse
from app.modules.repositories.service import RepositoryNotFoundError


router = APIRouter(prefix="/repositories", tags=["repository-knowledge"])


@router.get(
    "/{repository_id}/knowledge",
    response_model=RepositoryKnowledgeItemListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_repository_knowledge_items(
    repository_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    source_type: str | None = Query(None, min_length=1),
    item_type: str | None = Query(None, min_length=1),
    path_prefix: str | None = Query(None, min_length=1),
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryKnowledgeService = Depends(get_repository_knowledge_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryKnowledgeItemListResponse:
    try:
        return await service.list_repository_knowledge_items(
            session,
            repository_id,
            current_user.id,
            page,
            page_size,
            source_type,
            item_type,
            path_prefix,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc
