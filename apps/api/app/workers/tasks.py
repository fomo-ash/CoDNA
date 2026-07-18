from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.core.celery import celery_app
from app.core.config import get_settings
from app.db.models.job import Job
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.user import User
from app.modules.files.discovery import RepositoryFileDiscoveryService
from app.modules.files.service import RepositoryFileServiceImpl
from app.modules.jobs.enums import JobStatus
from app.modules.knowledge.service import KnowledgeExtractionContext, RepositoryKnowledgeServiceImpl
from app.modules.parsing.results import RepositoryParseResult, parse_result_from_dict
from app.modules.parsing.service import RepositoryParserServiceImpl
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
            job.completed_at = None
            job.error_message = None
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
            _job, repository, _user = await _get_job_and_repository(session, job_id, repository_id)
            repository.status = RepositoryStatus.INDEXING
            repository.clone_path = str(clone_result.clone_path)
            repository.last_cloned_at = clone_result.cloned_at
            await session.commit()

        file_discovery_service = RepositoryFileDiscoveryService(
            max_file_size_bytes=settings.repository_file_max_bytes,
            max_files=settings.repository_file_discovery_limit,
        )
        discovery_result = await asyncio.to_thread(
            file_discovery_service.discover,
            clone_result.clone_path,
        )
        logger.info(
            "repository file discovery completed job_id=%s repository_id=%s files=%s",
            job_id,
            repository_id,
            discovery_result.stats.total_files,
        )

        async with worker_session() as session:
            job, repository, _user = await _get_job_and_repository(session, job_id, repository_id)
            repository.status = RepositoryStatus.READY
            repository.clone_path = str(clone_result.clone_path)
            repository.last_cloned_at = clone_result.cloned_at
            await RepositoryFileServiceImpl().replace_repository_inventory(
                session,
                repository.id,
                discovery_result,
            )
            await session.flush()

            file_rows_result = await session.execute(
                select(RepositoryFile).where(RepositoryFile.repository_id == repository.id)
            )
            repository_files = file_rows_result.scalars().all()
            parse_result = _parse_repository_in_subprocess(clone_result.clone_path, repository_files)
            logger.info(
                "repository parsing completed job_id=%s repository_id=%s files=%s parsed=%s syntax_errors=%s unsupported=%s",
                job_id,
                repository_id,
                len(parse_result.files),
                parse_result.parsed_files,
                parse_result.syntax_error_files,
                parse_result.unsupported_files,
            )
            parser_service = RepositoryParserServiceImpl()
            await parser_service.replace_repository_parse_results(
                session,
                repository.id,
                parse_result,
            )
            knowledge_service = RepositoryKnowledgeServiceImpl()
            knowledge_result = knowledge_service.extract_repository(
                KnowledgeExtractionContext(
                    repository_id=repository.id,
                    repository_path=clone_result.clone_path,
                    files=repository_files,
                    parse_result=parse_result,
                )
            )
            logger.info(
                "repository knowledge extraction completed job_id=%s repository_id=%s items=%s",
                job_id,
                repository_id,
                knowledge_result.total_items,
            )
            await knowledge_service.replace_repository_knowledge(
                session,
                repository.id,
                knowledge_result,
            )

            job.status = JobStatus.COMPLETED
            completed_at = datetime.now(UTC)
            job.completed_at = completed_at
            job.error_message = None
            repository.last_indexed_at = completed_at
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


def _parse_repository_in_subprocess(
    repository_path: Path,
    repository_files,
) -> RepositoryParseResult:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as files_json:
        with tempfile.NamedTemporaryFile("r", encoding="utf-8", suffix=".json") as output_json:
            json.dump(
                [
                    {
                        "id": str(file.id),
                        "path": file.path,
                        "extension": file.extension,
                        "language": file.language,
                        "is_binary": file.is_binary,
                    }
                    for file in repository_files
                ],
                files_json,
            )
            files_json.flush()
            command = [
                sys.executable,
                "-m",
                "app.modules.parsing.cli",
                "--repository-path",
                str(repository_path),
                "--files-json",
                files_json.name,
                "--output-json",
                output_json.name,
            ]
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parents[2]),
            )
            if completed.returncode != 0:
                error_output = (completed.stderr or completed.stdout or "").strip()
                raise RuntimeError(
                    f"Repository parser subprocess failed with exit code {completed.returncode}: "
                    f"{error_output[:2000]}"
                )
            output_json.seek(0)
            return parse_result_from_dict(json.load(output_json))
