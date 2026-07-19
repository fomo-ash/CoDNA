from __future__ import annotations

from typing import Any

from app.modules.jobs.interfaces import JobService
from app.modules.jobs.service import JobServiceImpl


def get_job_service() -> JobService:
    return JobServiceImpl()


def get_repository_index_task() -> Any:
    from app.workers.tasks import run_repository_index

    return run_repository_index


def get_repository_embedding_task() -> Any:
    from app.workers.tasks import embed_repository_chunks

    return embed_repository_chunks
