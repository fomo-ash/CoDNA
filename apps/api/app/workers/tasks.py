from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.core.celery import celery_app
from app.db.models.job import Job
from app.db.models.repository import Repository
from app.modules.jobs.enums import JobStatus
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
            job, repository = await _get_job_and_repository(session, job_id, repository_id)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            repository.status = RepositoryStatus.INDEXING
            await session.commit()

        await asyncio.sleep(1)

        async with worker_session() as session:
            job, repository = await _get_job_and_repository(session, job_id, repository_id)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            repository.status = RepositoryStatus.READY
            repository.last_indexed_at = datetime.now(UTC)
            await session.commit()
        logger.info("repository indexing task completed job_id=%s repository_id=%s", job_id, repository_id)
    except Exception as exc:
        logger.exception("repository indexing task failed job_id=%s repository_id=%s", job_id, repository_id)
        await _mark_failed(job_id, repository_id, str(exc))
        raise


async def _get_job_and_repository(session, job_id: UUID, repository_id: UUID) -> tuple[Job, Repository]:
    result = await session.execute(
        select(Job, Repository)
        .join(Repository, Repository.id == Job.repository_id)
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
