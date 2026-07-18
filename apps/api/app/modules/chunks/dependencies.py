from __future__ import annotations

from app.modules.chunks.service import RepositoryChunkServiceImpl


def get_repository_chunk_service() -> RepositoryChunkServiceImpl:
    return RepositoryChunkServiceImpl()
