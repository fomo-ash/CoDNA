from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_relationship_edge import RepositoryRelationshipEdge
from app.modules.graph.schemas import RepositoryGraphResponse, RepositoryImpactResponse, RelationshipEdgeRead
from app.modules.repositories.service import RepositoryNotFoundError


class RepositoryGraphService:
    async def graph(self, session: AsyncSession, repository_id: UUID, owner_id: UUID, limit: int) -> RepositoryGraphResponse:
        await self._ensure_owner(session, repository_id, owner_id)
        rows = await session.scalars(select(RepositoryRelationshipEdge).where(
            RepositoryRelationshipEdge.repository_id == repository_id
        ).order_by(RepositoryRelationshipEdge.source_path, RepositoryRelationshipEdge.relationship_type).limit(limit))
        return RepositoryGraphResponse(repository_id=repository_id, edges=[RelationshipEdgeRead.model_validate(row) for row in rows])

    async def impact(self, session: AsyncSession, repository_id: UUID, owner_id: UUID, path: str, limit: int, include_unresolved: bool = False, include_tests: bool = False, include_internal: bool = False) -> RepositoryImpactResponse:
        await self._ensure_owner(session, repository_id, owner_id)
        rows = (await session.scalars(select(RepositoryRelationshipEdge).where(
            RepositoryRelationshipEdge.repository_id == repository_id,
            or_(RepositoryRelationshipEdge.source_path == path, RepositoryRelationshipEdge.target_path == path),
        ).order_by(RepositoryRelationshipEdge.source_path, RepositoryRelationshipEdge.relationship_type).limit(limit))).all()
        filtered = [row for row in rows if (include_unresolved or row.resolution == "resolved") and (include_tests or not self._is_test_path(row.source_path))]
        internal_rows = [row for row in filtered if row.source_path == path and row.target_path == path]
        external = [row for row in filtered if row not in internal_rows]
        incoming = self._deduplicate([row for row in external if row.target_path == path])
        outgoing = self._deduplicate([row for row in external if row.source_path == path])
        internal = self._deduplicate(internal_rows) if include_internal else []
        return RepositoryImpactResponse(repository_id=repository_id, path=path,
            incoming=[RelationshipEdgeRead.model_validate(row) for row in incoming],
            outgoing=[RelationshipEdgeRead.model_validate(row) for row in outgoing],
            internal=[RelationshipEdgeRead.model_validate(row) for row in internal],
            external_dependent_paths=sorted({row.source_path for row in incoming}))

    @staticmethod
    def _is_test_path(path: str) -> bool:
        name = path.rsplit("/", 1)[-1]
        return name.startswith("test_") or "/tests/" in f"/{path}"

    @staticmethod
    def _deduplicate(rows: list[RepositoryRelationshipEdge]) -> list[RepositoryRelationshipEdge]:
        seen: set[tuple[str, ...]] = set()
        result: list[RepositoryRelationshipEdge] = []
        for row in rows:
            key = (row.relationship_type, row.source_path, row.target_path or "", row.target_stable_symbol_id or "", row.target_symbol or "")
            if row.relationship_type == "imports":
                key = (row.relationship_type, row.source_path, row.target_path or "")
            if key not in seen:
                seen.add(key)
                result.append(row)
        return result

    async def _ensure_owner(self, session: AsyncSession, repository_id: UUID, owner_id: UUID) -> None:
        owned = await session.scalar(select(Repository.id).where(Repository.id == repository_id, Repository.owner_id == owner_id))
        if owned is None:
            raise RepositoryNotFoundError
