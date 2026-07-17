from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead


class RepositoryService(Protocol):
    async def list_repositories(self, session: AsyncSession) -> Sequence[RepositoryRead]:
        ...

    async def create_repository(
        self,
        session: AsyncSession,
        payload: RepositoryCreate,
    ) -> RepositoryRead:
        ...

    async def get_repository(
        self,
        session: AsyncSession,
        repository_id: UUID,
    ) -> RepositoryRead:
        ...
