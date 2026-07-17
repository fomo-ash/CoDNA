from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.github.schemas import GitHubRepository
from app.modules.repositories.schemas import RepositoryRead


class RepositoryService(Protocol):
    async def list_repositories(
        self,
        session: AsyncSession,
        owner_id: UUID,
    ) -> Sequence[RepositoryRead]:
        ...

    async def create_repository(
        self,
        session: AsyncSession,
        owner_id: UUID,
        github_repository: GitHubRepository,
    ) -> RepositoryRead:
        ...

    async def get_repository(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> RepositoryRead:
        ...
