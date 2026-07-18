from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SemanticChunk:
    repository_file_id: UUID | None
    path: str
    chunk_type: str
    source_type: str
    title: str
    language: str | None
    content: str
    start_line: int | None
    end_line: int | None
    metadata: dict
