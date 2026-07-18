from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.files.discovery import RepositoryDiscoveryResult
from app.modules.files.schemas import RepositoryFileListResponse, RepositoryStatsRead


class RepositoryFileService(Protocol):
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
        ...

    async def get_repository_stats(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> RepositoryStatsRead:
        ...

    async def replace_repository_inventory(
        self,
        session: AsyncSession,
        repository_id: UUID,
        discovery_result: RepositoryDiscoveryResult,
    ) -> None:
        ...
