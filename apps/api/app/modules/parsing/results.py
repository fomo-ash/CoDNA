from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from app.modules.parsing.enums import RepositoryFileParseStatus


@dataclass(frozen=True)
class ParsedRepositoryFile:
    repository_file_id: UUID
    path: str
    language: str | None
    parser: str | None
    status: RepositoryFileParseStatus
    root_node_type: str | None = None
    has_error: bool = False
    error_count: int = 0
    symbols: list[dict] = field(default_factory=list)
    imports: list[dict] = field(default_factory=list)
    parsed_at: datetime | None = None
    error_message: str | None = None

    @property
    def symbol_count(self) -> int:
        return len(self.symbols)

    @property
    def import_count(self) -> int:
        return len(self.imports)


@dataclass(frozen=True)
class RepositoryParseResult:
    files: list[ParsedRepositoryFile]
    parsed_files: int
    syntax_error_files: int
    unsupported_files: int
    skipped_files: int
    failed_files: int


def parse_result_to_dict(parse_result: RepositoryParseResult) -> dict:
    return {
        "files": [
            {
                "repository_file_id": str(file.repository_file_id),
                "path": file.path,
                "language": file.language,
                "parser": file.parser,
                "status": file.status.value,
                "root_node_type": file.root_node_type,
                "has_error": file.has_error,
                "error_count": file.error_count,
                "symbols": file.symbols,
                "imports": file.imports,
                "parsed_at": file.parsed_at.isoformat() if file.parsed_at else None,
                "error_message": file.error_message,
            }
            for file in parse_result.files
        ],
        "parsed_files": parse_result.parsed_files,
        "syntax_error_files": parse_result.syntax_error_files,
        "unsupported_files": parse_result.unsupported_files,
        "skipped_files": parse_result.skipped_files,
        "failed_files": parse_result.failed_files,
    }


def parse_result_from_dict(data: dict) -> RepositoryParseResult:
    files = [
        ParsedRepositoryFile(
            repository_file_id=UUID(file["repository_file_id"]),
            path=file["path"],
            language=file.get("language"),
            parser=file.get("parser"),
            status=RepositoryFileParseStatus(file["status"]),
            root_node_type=file.get("root_node_type"),
            has_error=file.get("has_error", False),
            error_count=file.get("error_count", 0),
            symbols=file.get("symbols", []),
            imports=file.get("imports", []),
            parsed_at=_parse_datetime(file.get("parsed_at")),
            error_message=file.get("error_message"),
        )
        for file in data.get("files", [])
    ]
    return RepositoryParseResult(
        files=files,
        parsed_files=data.get("parsed_files", 0),
        syntax_error_files=data.get("syntax_error_files", 0),
        unsupported_files=data.get("unsupported_files", 0),
        skipped_files=data.get("skipped_files", 0),
        failed_files=data.get("failed_files", 0),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
