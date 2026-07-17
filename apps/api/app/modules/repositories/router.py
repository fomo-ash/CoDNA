from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.github.dependencies import get_github_service
from app.modules.github.service import (
    GitHubAuthorizationRequiredError,
    GitHubIntegrationError,
    GitHubRepositoryNotFoundError,
    GitHubServiceImpl,
)
from app.modules.jobs.dependencies import get_job_service, get_repository_index_task
from app.modules.jobs.interfaces import JobService
from app.modules.jobs.schemas import RepositoryIndexJobResponse
from app.modules.jobs.service import JobRepositoryNotFoundError
from app.modules.repositories.dependencies import get_repository_service
from app.modules.repositories.interfaces import RepositoryService
from app.modules.repositories.schemas import RepositoryImportRequest, RepositoryRead
from app.modules.repositories.service import RepositoryAlreadyExistsError, RepositoryNotFoundError


router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryRead], status_code=status.HTTP_200_OK)
async def list_repositories(
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
    current_user: User = Depends(get_current_user_record),
) -> list[RepositoryRead]:
    return list(await service.list_repositories(session, current_user.id))


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryImportRequest,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
    current_user: User = Depends(get_current_user_record),
    github_service: GitHubServiceImpl = Depends(get_github_service),
) -> RepositoryRead:
    try:
        github_repository = await github_service.get_repository(
            current_user,
            github_id=payload.github_id,
            full_name=payload.full_name,
        )
        return await service.create_repository(session, current_user.id, github_repository)
    except GitHubAuthorizationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub authorization is required.",
        ) from exc
    except GitHubRepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub repository not found.",
        ) from exc
    except GitHubIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repository request failed.",
        ) from exc
    except RepositoryAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A repository with this full_name already exists.",
        ) from exc


@router.get("/{repository_id}", response_model=RepositoryRead, status_code=status.HTTP_200_OK)
async def get_repository(
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryService = Depends(get_repository_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryRead:
    try:
        return await service.get_repository(session, repository_id, current_user.id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc


@router.post(
    "/{repository_id}/index",
    response_model=RepositoryIndexJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user_record),
    session: AsyncSession = Depends(get_db_session),
    job_service: JobService = Depends(get_job_service),
    index_task=Depends(get_repository_index_task),
) -> RepositoryIndexJobResponse:
    try:
        job, created = await job_service.create_repository_index_job(
            session,
            repository_id,
            current_user.id,
        )
    except JobRepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found.",
        ) from exc

    if created:
        try:
            task_result = index_task.delay(str(job.id), str(repository_id))
            job = await job_service.attach_celery_task(session, job.id, task_result.id)
        except Exception as exc:
            await job_service.mark_failed(session, job.id, "Failed to enqueue indexing task.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to enqueue indexing task.",
            ) from exc

    return RepositoryIndexJobResponse(
        repository_id=repository_id,
        job_id=job.id,
        status=job.status,
    )
