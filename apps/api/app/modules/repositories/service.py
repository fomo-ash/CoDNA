from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repositories.schemas import RepositoryCreate, RepositoryRead


class RepositoryServiceStub:
    async def list_repositories(self, session: AsyncSession) -> list[RepositoryRead]:
        del session
        raise NotImplementedError("Repository listing is not implemented yet.")

    async def create_repository(
        self,
        session: AsyncSession,
        payload: RepositoryCreate,
    ) -> RepositoryRead:
        del session, payload
        raise NotImplementedError("Repository registration is not implemented yet.")

    async def get_repository(
        self,
        session: AsyncSession,
        repository_id: UUID,
    ) -> RepositoryRead:
        del session, repository_id
        raise NotImplementedError("Repository lookup is not implemented yet.")
