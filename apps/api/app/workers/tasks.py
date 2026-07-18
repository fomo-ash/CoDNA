from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.celery import celery_app
from app.core.config import get_settings
from app.db.models.job import Job
from app.db.models.repository import Repository
from app.db.models.user import User
from app.modules.jobs.enums import JobStatus
from app.modules.repositories.clone import RepositoryCloneService, RepositoryCloneTarget
from app.modules.repositories.enums import RepositoryStatus
from app.workers.database import worker_session


logger = logging.getLogger("app.workers.repository_index")


@celery_app.task(name="app.workers.tasks.run_repository_index")
def run_repository_index(job_id: str, repository_id: str) -> None:
    asyncio.run(_run_repository_index(UUID(job_id), UUID(repository_id)))


async def _run_repository_index(job_id: UUID, repository_id: UUID) -> None:
    logger.info("repository indexing task started job_id=%s repository_id=%s", job_id, repository_id)
    try:
        async with worker_session() as session:
            job, repository, user = await _get_job_and_repository(session, job_id, repository_id)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            repository.status = RepositoryStatus.CLONING
            await session.commit()

        settings = get_settings()
        clone_service = RepositoryCloneService(settings.repository_workspace_path)
        clone_result = await clone_service.clone_repository(
            RepositoryCloneTarget(
                repository_id=repository.id,
                clone_url=repository.clone_url,
                default_branch=repository.default_branch,
                github_access_token=user.github_access_token
                if user and repository.visibility == "private"
                else None,
            )
        )

        async with worker_session() as session:
            job, repository, _user = await _get_job_and_repository(session, job_id, repository_id)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            repository.status = RepositoryStatus.READY
            repository.clone_path = str(clone_result.clone_path)
            repository.last_cloned_at = clone_result.cloned_at
            await session.commit()
        logger.info("repository indexing task completed job_id=%s repository_id=%s", job_id, repository_id)
    except Exception as exc:
        logger.exception("repository indexing task failed job_id=%s repository_id=%s", job_id, repository_id)
        await _mark_failed(job_id, repository_id, str(exc))
        raise


async def _get_job_and_repository(
    session,
    job_id: UUID,
    repository_id: UUID,
) -> tuple[Job, Repository, User | None]:
    result = await session.execute(
        select(Job, Repository, User)
        .join(Repository, Repository.id == Job.repository_id)
        .outerjoin(User, User.id == Repository.owner_id)
        .where(Job.id == job_id, Repository.id == repository_id)
    )
    row = result.one_or_none()
    if row is None:
        raise RuntimeError("Repository indexing job was not found.")
    return row


async def _mark_failed(job_id: UUID, repository_id: UUID, error_message: str) -> None:
    async with worker_session() as session:
        result = await session.execute(
            select(Job, Repository)
            .join(Repository, Repository.id == Job.repository_id)
            .where(Job.id == job_id, Repository.id == repository_id)
        )
        row = result.one_or_none()
        if row is None:
            return

        job, repository = row
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        repository.status = RepositoryStatus.FAILED
        await session.commit()
