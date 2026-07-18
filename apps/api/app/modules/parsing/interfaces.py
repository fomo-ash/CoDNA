from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository_file import RepositoryFile
from app.modules.parsing.results import RepositoryParseResult
from app.modules.parsing.schemas import RepositoryFileParseListResponse


class RepositoryParserService(Protocol):
    async def list_repository_parse_results(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
        page: int,
        page_size: int,
        status: str | None = None,
        language: str | None = None,
        path_prefix: str | None = None,
    ) -> RepositoryFileParseListResponse:
        ...

    def parse_repository(
        self,
        repository_path: Path,
        files: Iterable[RepositoryFile],
    ) -> RepositoryParseResult:
        ...

    async def replace_repository_parse_results(
        self,
        session: AsyncSession,
        repository_id: UUID,
        parse_result: RepositoryParseResult,
    ) -> None:
        ...
