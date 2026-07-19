from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.github.client import GitHubClient
from app.modules.history.schemas import RepositoryHistoryListResponse
from app.modules.history.service import RepositoryHistoryService


router = APIRouter(prefix="/repositories", tags=["repository-history"])


@router.get("/{repository_id}/history", response_model=RepositoryHistoryListResponse)
async def list_repository_history(
    repository_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryHistoryListResponse:
    artifacts = await RepositoryHistoryService(GitHubClient(get_settings())).list(
        session, repository_id, current_user.id, limit
    )
    return RepositoryHistoryListResponse(repository_id=repository_id, artifacts=artifacts)
