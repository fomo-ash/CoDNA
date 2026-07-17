from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import Job
from app.db.models.repository import Repository
from app.modules.jobs.enums import JobStatus, JobType
from app.modules.jobs.schemas import JobRead
from app.modules.repositories.enums import RepositoryStatus


class JobNotFoundError(Exception):
    pass


class JobRepositoryNotFoundError(Exception):
    pass


class JobServiceImpl:
    async def get_job(
        self,
        session: AsyncSession,
        job_id: UUID,
        owner_id: UUID,
    ) -> JobRead:
        result = await session.execute(
            select(Job)
            .join(Repository, Repository.id == Job.repository_id)
            .where(Job.id == job_id, Repository.owner_id == owner_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError
        return JobRead.model_validate(job)

    async def create_repository_index_job(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> tuple[JobRead, bool]:
        repository_result = await session.execute(
            select(Repository).where(
                Repository.id == repository_id,
                Repository.owner_id == owner_id,
            )
        )
        repository = repository_result.scalar_one_or_none()
        if repository is None:
            raise JobRepositoryNotFoundError

        active_job_result = await session.execute(
            select(Job)
            .where(
                Job.repository_id == repository_id,
                Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
            )
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        active_job = active_job_result.scalar_one_or_none()
        if active_job is not None:
            return JobRead.model_validate(active_job), False

        job = Job(
            repository_id=repository_id,
            job_type=JobType.REPOSITORY_INDEX,
            status=JobStatus.QUEUED,
        )
        repository.status = RepositoryStatus.INDEXING
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return JobRead.model_validate(job), True

    async def attach_celery_task(
        self,
        session: AsyncSession,
        job_id: UUID,
        celery_task_id: str,
    ) -> JobRead:
        job = await self._get_job_record(session, job_id)
        job.celery_task_id = celery_task_id
        await session.commit()
        await session.refresh(job)
        return JobRead.model_validate(job)

    async def mark_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        error_message: str,
    ) -> JobRead:
        job = await self._get_job_record(session, job_id)
        repository_result = await session.execute(
            select(Repository).where(Repository.id == job.repository_id)
        )
        repository = repository_result.scalar_one_or_none()
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        if repository is not None:
            repository.status = RepositoryStatus.FAILED
        await session.commit()
        await session.refresh(job)
        return JobRead.model_validate(job)

    async def _get_job_record(self, session: AsyncSession, job_id: UUID) -> Job:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError
        return job
