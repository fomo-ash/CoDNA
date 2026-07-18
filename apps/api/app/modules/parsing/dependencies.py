from __future__ import annotations

from app.modules.parsing.interfaces import RepositoryParserService
from app.modules.parsing.service import RepositoryParserServiceImpl


def get_repository_parser_service() -> RepositoryParserService:
    return RepositoryParserServiceImpl()
