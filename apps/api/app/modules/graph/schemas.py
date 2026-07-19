from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class RelationshipEdgeRead(BaseModel):
    id: UUID
    source_chunk_id: UUID
    target_chunk_id: UUID | None
    relationship_type: str
    source_path: str
    source_stable_symbol_id: str | None
    target_path: str | None
    target_stable_symbol_id: str | None
    target_symbol: str | None
    resolution: str

    model_config = {"from_attributes": True}


class RepositoryGraphResponse(BaseModel):
    repository_id: UUID
    edges: list[RelationshipEdgeRead]


class RepositoryImpactResponse(BaseModel):
    repository_id: UUID
    path: str
    incoming: list[RelationshipEdgeRead]
    outgoing: list[RelationshipEdgeRead]
    internal: list[RelationshipEdgeRead] = []
    external_dependent_paths: list[str] = []


class RepositoryImpactTraversalResponse(BaseModel):
    repository_id: UUID
    path: str
    depth: int
    affected_paths: list[str]
    paths: list[list[str]]


class RepositorySymbolImpactTraversalResponse(BaseModel):
    """Resolved reverse dependency paths for one stable repository symbol."""

    repository_id: UUID
    stable_symbol_id: str
    depth: int
    affected_symbol_ids: list[str]
    affected_paths: list[str]
    paths: list[list[str]]
