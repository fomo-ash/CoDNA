from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.modules.github.schemas import GitHubRepository
from app.modules.repositories.enums import RepositoryStatus
from app.modules.repositories.schemas import RepositoryRead


class RepositoryNotFoundError(Exception):
    pass


class RepositoryAlreadyExistsError(Exception):
    pass


class RepositoryServiceImpl:
    async def list_repositories(
        self,
        session: AsyncSession,
        owner_id: UUID,
    ) -> list[RepositoryRead]:
        result = await session.execute(
            select(Repository)
            .where(Repository.owner_id == owner_id)
            .order_by(Repository.created_at.desc())
        )
        return [RepositoryRead.model_validate(repository) for repository in result.scalars().all()]

    async def create_repository(
        self,
        session: AsyncSession,
        owner_id: UUID,
        github_repository: GitHubRepository,
    ) -> RepositoryRead:
        repository = Repository(
            owner_id=owner_id,
            github_id=github_repository.github_id,
            name=github_repository.name,
            full_name=github_repository.full_name,
            default_branch=github_repository.default_branch,
            clone_url=github_repository.clone_url,
            visibility=github_repository.visibility,
            status=RepositoryStatus.REGISTERED,
        )
        session.add(repository)

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise RepositoryAlreadyExistsError from exc

        await session.refresh(repository)
        return RepositoryRead.model_validate(repository)

    async def get_repository(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> RepositoryRead:
        result = await session.execute(
            select(Repository).where(
                Repository.id == repository_id,
                Repository.owner_id == owner_id,
            )
        )
        repository = result.scalar_one_or_none()
        if repository is None:
            raise RepositoryNotFoundError
        return RepositoryRead.model_validate(repository)
