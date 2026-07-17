from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.schemas import JobRead


class JobService(Protocol):
    async def get_job(
        self,
        session: AsyncSession,
        job_id: UUID,
        owner_id: UUID,
    ) -> JobRead:
        ...

    async def create_repository_index_job(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> tuple[JobRead, bool]:
        ...

    async def attach_celery_task(
        self,
        session: AsyncSession,
        job_id: UUID,
        celery_task_id: str,
    ) -> JobRead:
        ...

    async def mark_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        error_message: str,
    ) -> JobRead:
        ...
