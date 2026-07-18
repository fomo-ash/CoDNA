from __future__ import annotations

from app.modules.files.interfaces import RepositoryFileService
from app.modules.files.service import RepositoryFileServiceImpl


def get_repository_file_service() -> RepositoryFileService:
    return RepositoryFileServiceImpl()
