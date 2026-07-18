from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_chunk import RepositoryChunk
from app.db.models.repository_knowledge_item import RepositoryKnowledgeItem
from app.modules.chunks.builder import SemanticChunkBuilder
from app.modules.chunks.schemas import RepositoryChunkListResponse, RepositoryChunkRead
from app.modules.repositories.service import RepositoryNotFoundError


class RepositoryChunkNotFoundError(Exception):
    pass


class RepositoryChunkServiceImpl:
    def __init__(self, builder: SemanticChunkBuilder | None = None) -> None:
        self.builder = builder or SemanticChunkBuilder()

    async def rebuild_repository_chunks(
        self, session: AsyncSession, repository_id: UUID, repository_path: Path
    ) -> int:
        result = await session.execute(
            select(RepositoryKnowledgeItem)
            .where(RepositoryKnowledgeItem.repository_id == repository_id)
            .order_by(RepositoryKnowledgeItem.path, RepositoryKnowledgeItem.item_type, RepositoryKnowledgeItem.name)
        )
        chunks = self.builder.build(repository_path, result.scalars().all(), repository_id)
        for chunk in chunks:
            chunk.metadata["repository_file_id"] = (
                str(chunk.repository_file_id) if chunk.repository_file_id else None
            )
        await session.execute(delete(RepositoryChunk).where(RepositoryChunk.repository_id == repository_id))
        session.add_all(
            [
                RepositoryChunk(
                    repository_id=repository_id,
                    repository_file_id=chunk.repository_file_id,
                    path=chunk.path,
                    chunk_type=chunk.chunk_type,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    language=chunk.language,
                    content=chunk.content,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    metadata_=chunk.metadata,
                )
                for chunk in chunks
            ]
        )
        return len(chunks)

    async def list_repository_chunks(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
        page: int,
        page_size: int,
        source_type: str | None = None,
        chunk_type: str | None = None,
    ) -> RepositoryChunkListResponse:
        await self._ensure_repository_owner(session, repository_id, owner_id)
        filters = [RepositoryChunk.repository_id == repository_id]
        if source_type:
            filters.append(RepositoryChunk.source_type == source_type)
        if chunk_type:
            filters.append(RepositoryChunk.chunk_type == chunk_type)
        result = await session.execute(
            select(RepositoryChunk)
            .where(*filters)
            .order_by(RepositoryChunk.path, RepositoryChunk.start_line, RepositoryChunk.title)
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        chunks = result.scalars().all()
        return RepositoryChunkListResponse(
            chunks=[RepositoryChunkRead.model_validate(chunk) for chunk in chunks[:page_size]],
            page=page,
            page_size=page_size,
            has_next_page=len(chunks) > page_size,
        )

    async def get_chunk(self, session: AsyncSession, chunk_id: UUID, owner_id: UUID) -> RepositoryChunkRead:
        result = await session.execute(
            select(RepositoryChunk)
            .join(Repository, Repository.id == RepositoryChunk.repository_id)
            .where(RepositoryChunk.id == chunk_id, Repository.owner_id == owner_id)
        )
        chunk = result.scalar_one_or_none()
        if chunk is None:
            raise RepositoryChunkNotFoundError
        return RepositoryChunkRead.model_validate(chunk)

    async def _ensure_repository_owner(self, session: AsyncSession, repository_id: UUID, owner_id: UUID) -> None:
        result = await session.execute(
            select(Repository.id).where(Repository.id == repository_id, Repository.owner_id == owner_id)
        )
        if result.scalar_one_or_none() is None:
            raise RepositoryNotFoundError
