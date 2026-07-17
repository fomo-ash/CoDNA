from __future__ import annotations

from app.modules.repositories.interfaces import RepositoryService
from app.modules.repositories.service import RepositoryServiceStub


def get_repository_service() -> RepositoryService:
    return RepositoryServiceStub()
