from __future__ import annotations

from app.modules.repositories.interfaces import RepositoryService
from app.modules.repositories.service import RepositoryServiceImpl


def get_repository_service() -> RepositoryService:
    return RepositoryServiceImpl()
