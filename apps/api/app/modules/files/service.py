from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_statistics import RepositoryStatistics
from app.modules.files.discovery import RepositoryDiscoveryResult
from app.modules.files.schemas import (
    RepositoryFileListResponse,
    RepositoryFileRead,
    RepositoryStatsRead,
)
from app.modules.repositories.service import RepositoryNotFoundError


@dataclass(frozen=True)
class RepositoryInventoryDelta:
    """The content-level change set produced by an inventory scan."""

    changed_files: list[RepositoryFile]
    removed_paths: list[str]

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_files or self.removed_paths)


class RepositoryFileServiceImpl:
    async def list_repository_files(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
        page: int,
        page_size: int,
        language: str | None = None,
        extension: str | None = None,
        path_prefix: str | None = None,
    ) -> RepositoryFileListResponse:
        await self._ensure_repository_owner(session, repository_id, owner_id)

        filters = [RepositoryFile.repository_id == repository_id]
        if language:
            filters.append(RepositoryFile.language == language)
        if extension:
            filters.append(RepositoryFile.extension == extension.lower().removeprefix("."))
        if path_prefix:
            filters.append(RepositoryFile.path.startswith(path_prefix))

        result = await session.execute(
            select(RepositoryFile)
            .where(*filters)
            .order_by(RepositoryFile.path.asc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        files = result.scalars().all()
        return RepositoryFileListResponse(
            files=[RepositoryFileRead.model_validate(file) for file in files[:page_size]],
            page=page,
            page_size=page_size,
            has_next_page=len(files) > page_size,
        )

    async def get_repository_stats(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> RepositoryStatsRead:
        await self._ensure_repository_owner(session, repository_id, owner_id)

        result = await session.execute(
            select(RepositoryStatistics).where(RepositoryStatistics.repository_id == repository_id)
        )
        stats = result.scalar_one_or_none()
        if stats is None:
            return RepositoryStatsRead(
                repository_id=repository_id,
                total_files=0,
                source_files=0,
                binary_files=0,
                total_size_bytes=0,
                languages={},
                last_scan_at=None,
            )

        return RepositoryStatsRead(
            repository_id=stats.repository_id,
            total_files=stats.total_files,
            source_files=stats.source_files,
            binary_files=stats.binary_files,
            total_size_bytes=stats.total_size_bytes,
            languages=stats.detected_languages,
            last_scan_at=stats.last_scan_at,
        )

    async def replace_repository_inventory(
        self,
        session: AsyncSession,
        repository_id: UUID,
        discovery_result: RepositoryDiscoveryResult,
    ) -> None:
        await session.execute(delete(RepositoryFile).where(RepositoryFile.repository_id == repository_id))
        session.add_all(
            [
                RepositoryFile(
                    repository_id=repository_id,
                    path=file.path,
                    filename=file.filename,
                    extension=file.extension,
                    language=file.language,
                    size_bytes=file.size_bytes,
                    sha256=file.sha256,
                    is_binary=file.is_binary,
                    discovered_at=file.discovered_at,
                )
                for file in discovery_result.files
            ]
        )

        stats_result = await session.execute(
            select(RepositoryStatistics).where(RepositoryStatistics.repository_id == repository_id)
        )
        stats = stats_result.scalar_one_or_none()
        if stats is None:
            stats = RepositoryStatistics(repository_id=repository_id)
            session.add(stats)

        stats.total_files = discovery_result.stats.total_files
        stats.source_files = discovery_result.stats.source_files
        stats.binary_files = discovery_result.stats.binary_files
        stats.total_size_bytes = discovery_result.stats.total_size_bytes
        stats.detected_languages = discovery_result.stats.detected_languages
        stats.last_scan_at = discovery_result.stats.last_scan_at

    async def synchronize_repository_inventory(
        self,
        session: AsyncSession,
        repository_id: UUID,
        discovery_result: RepositoryDiscoveryResult,
    ) -> RepositoryInventoryDelta:
        """Persist an inventory scan while retaining rows for unchanged content."""
        existing_result = await session.execute(
            select(RepositoryFile).where(RepositoryFile.repository_id == repository_id)
        )
        existing_by_path = {file.path: file for file in existing_result.scalars().all()}
        discovered_by_path = {file.path: file for file in discovery_result.files}

        changed_files: list[RepositoryFile] = []
        for path, discovered in discovered_by_path.items():
            current = existing_by_path.pop(path, None)
            if current is None:
                current = RepositoryFile(repository_id=repository_id, path=path)
                session.add(current)
                changed_files.append(current)
            elif current.sha256 != discovered.sha256:
                changed_files.append(current)

            current.filename = discovered.filename
            current.extension = discovered.extension
            current.language = discovered.language
            current.size_bytes = discovered.size_bytes
            current.sha256 = discovered.sha256
            current.is_binary = discovered.is_binary
            current.discovered_at = discovered.discovered_at

        removed_paths = sorted(existing_by_path)
        if removed_paths:
            await session.execute(
                delete(RepositoryFile).where(
                    RepositoryFile.repository_id == repository_id,
                    RepositoryFile.path.in_(removed_paths),
                )
            )

        stats_result = await session.execute(
            select(RepositoryStatistics).where(RepositoryStatistics.repository_id == repository_id)
        )
        stats = stats_result.scalar_one_or_none()
        if stats is None:
            stats = RepositoryStatistics(repository_id=repository_id)
            session.add(stats)

        stats.total_files = discovery_result.stats.total_files
        stats.source_files = discovery_result.stats.source_files
        stats.binary_files = discovery_result.stats.binary_files
        stats.total_size_bytes = discovery_result.stats.total_size_bytes
        stats.detected_languages = discovery_result.stats.detected_languages
        stats.last_scan_at = discovery_result.stats.last_scan_at
        await session.flush()
        return RepositoryInventoryDelta(changed_files=changed_files, removed_paths=removed_paths)

    async def _ensure_repository_owner(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> None:
        result = await session.execute(
            select(Repository.id).where(
                Repository.id == repository_id,
                Repository.owner_id == owner_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise RepositoryNotFoundError
