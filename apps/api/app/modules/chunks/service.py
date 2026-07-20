from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_chunk import RepositoryChunk
from app.db.models.repository_knowledge_item import RepositoryKnowledgeItem
from app.db.models.repository_relationship_edge import RepositoryRelationshipEdge
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
        await session.execute(delete(RepositoryRelationshipEdge).where(RepositoryRelationshipEdge.repository_id == repository_id))
        await session.execute(delete(RepositoryChunk).where(RepositoryChunk.repository_id == repository_id))
        persisted_chunks = [
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
        session.add_all(persisted_chunks)
        await session.flush()
        self._materialize_relationship_edges(repository_id, persisted_chunks, session)
        return len(chunks)

    async def rebuild_changed_repository_chunks(
        self,
        session: AsyncSession,
        repository_id: UUID,
        repository_path: Path,
        paths: set[str],
    ) -> int:
        """Replace chunks for changed paths and rebuild their repository graph edges."""
        if not paths:
            return 0
        result = await session.execute(
            select(RepositoryKnowledgeItem)
            .where(RepositoryKnowledgeItem.repository_id == repository_id)
            .order_by(RepositoryKnowledgeItem.path, RepositoryKnowledgeItem.item_type, RepositoryKnowledgeItem.name)
        )
        chunks = self.builder.build(repository_path, result.scalars().all(), repository_id)
        changed_chunks = [chunk for chunk in chunks if chunk.path in paths]
        for chunk in changed_chunks:
            chunk.metadata["repository_file_id"] = (
                str(chunk.repository_file_id) if chunk.repository_file_id else None
            )

        # Existing edges can reference replaced chunks. Re-materialize them from
        # the current chunk metadata after replacing only the affected paths.
        await session.execute(
            delete(RepositoryRelationshipEdge).where(RepositoryRelationshipEdge.repository_id == repository_id)
        )
        await session.execute(
            delete(RepositoryChunk).where(
                RepositoryChunk.repository_id == repository_id,
                RepositoryChunk.path.in_(paths),
            )
        )
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
                for chunk in changed_chunks
            ]
        )
        await session.flush()
        persisted = await session.scalars(
            select(RepositoryChunk).where(RepositoryChunk.repository_id == repository_id)
        )
        self._materialize_relationship_edges(repository_id, persisted.all(), session)
        return len(changed_chunks)

    @staticmethod
    def _materialize_relationship_edges(
        repository_id: UUID, chunks: list[RepositoryChunk], session: AsyncSession
    ) -> None:
        by_symbol: dict[str, RepositoryChunk] = {}
        by_path: dict[str, RepositoryChunk] = {}
        for chunk in chunks:
            by_path.setdefault(chunk.path, chunk)
            stable_id = chunk.metadata_.get("stable_symbol_id")
            if isinstance(stable_id, str):
                by_symbol.setdefault(stable_id, chunk)

        edges: list[RepositoryRelationshipEdge] = []
        for chunk in chunks:
            relationships = chunk.metadata_.get("relationships", {})
            source_symbol = chunk.metadata_.get("stable_symbol_id")
            for relationship_type in ("imports", "calls", "references", "inherits", "implements"):
                for relationship in relationships.get(relationship_type, []):
                    relation = relationship if isinstance(relationship, dict) else {"symbol": relationship}
                    target_stable_id = relation.get("stable_symbol_id")
                    target_path = relation.get("path")
                    target = (
                        by_symbol.get(target_stable_id) if isinstance(target_stable_id, str) else None
                    ) or (by_path.get(target_path) if isinstance(target_path, str) else None)
                    edges.append(RepositoryRelationshipEdge(
                        repository_id=repository_id,
                        source_chunk_id=chunk.id,
                        target_chunk_id=target.id if target else None,
                        relationship_type=relationship_type,
                        source_path=chunk.path,
                        source_stable_symbol_id=source_symbol if isinstance(source_symbol, str) else None,
                        target_path=target_path if isinstance(target_path, str) else None,
                        target_stable_symbol_id=target_stable_id if isinstance(target_stable_id, str) else None,
                        target_symbol=relation.get("symbol") if isinstance(relation.get("symbol"), str) else None,
                        resolution="resolved" if target else "unresolved",
                    ))
        session.add_all(edges)

    async def list_repository_chunks(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
        page: int,
        page_size: int,
        source_type: str | None = None,
        chunk_type: str | None = None,
        search: str | None = None,
    ) -> RepositoryChunkListResponse:
        await self._ensure_repository_owner(session, repository_id, owner_id)
        filters = [RepositoryChunk.repository_id == repository_id]
        if source_type:
            filters.append(RepositoryChunk.source_type == source_type)
        if chunk_type:
            filters.append(RepositoryChunk.chunk_type == chunk_type)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filters.append(or_(
                RepositoryChunk.path.ilike(pattern),
                RepositoryChunk.title.ilike(pattern),
                RepositoryChunk.content.ilike(pattern),
            ))
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
