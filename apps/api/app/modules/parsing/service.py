from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from tree_sitter import Language, Node, Parser

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from app.db.models.repository import Repository
from app.db.models.repository_file import RepositoryFile
from app.db.models.repository_file_parse import RepositoryFileParse
from app.modules.parsing.enums import RepositoryFileParseStatus
from app.modules.parsing.results import ParsedRepositoryFile, RepositoryParseResult
from app.modules.parsing.schemas import (
    RepositoryFileParseListResponse,
    RepositoryFileParseRead,
)
from app.modules.repositories.service import RepositoryNotFoundError


SUPPORTED_GRAMMARS = {
    "py": ("python", lambda: Language(tree_sitter_python.language())),
    "js": ("javascript", lambda: Language(tree_sitter_javascript.language())),
    "jsx": ("javascript", lambda: Language(tree_sitter_javascript.language())),
    "ts": ("typescript", lambda: Language(tree_sitter_typescript.language_typescript())),
    "tsx": ("tsx", lambda: Language(tree_sitter_typescript.language_tsx())),
}

SYMBOL_NODE_TYPES = {
    "class_definition": "class",
    "class_declaration": "class",
    "enum_declaration": "enum",
    "function_definition": "function",
    "function_declaration": "function",
    "interface_declaration": "interface",
    "method_definition": "method",
    "type_alias_declaration": "type",
}

IMPORT_NODE_TYPES = {
    "import_statement",
    "import_from_statement",
}


class RepositoryParserServiceImpl:
    def __init__(self) -> None:
        self._parsers: dict[str, tuple[str, Parser]] = {}

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
        await self._ensure_repository_owner(session, repository_id, owner_id)

        filters = [RepositoryFileParse.repository_id == repository_id]
        if status:
            filters.append(RepositoryFileParse.status == status)
        if language:
            filters.append(RepositoryFileParse.language == language)
        if path_prefix:
            filters.append(RepositoryFileParse.path.startswith(path_prefix))

        result = await session.execute(
            select(RepositoryFileParse)
            .where(*filters)
            .order_by(RepositoryFileParse.path.asc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        parse_results = result.scalars().all()
        return RepositoryFileParseListResponse(
            parse_results=[
                RepositoryFileParseRead.model_validate(parse_result)
                for parse_result in parse_results[:page_size]
            ],
            page=page,
            page_size=page_size,
            has_next_page=len(parse_results) > page_size,
        )

    def parse_repository(
        self,
        repository_path: Path,
        files: Iterable[RepositoryFile],
    ) -> RepositoryParseResult:
        root = Path(repository_path).resolve()
        results = [self.parse_file(root, file) for file in files]
        return RepositoryParseResult(
            files=results,
            parsed_files=sum(1 for file in results if file.status == RepositoryFileParseStatus.PARSED),
            syntax_error_files=sum(
                1 for file in results if file.status == RepositoryFileParseStatus.SYNTAX_ERROR
            ),
            unsupported_files=sum(
                1 for file in results if file.status == RepositoryFileParseStatus.UNSUPPORTED
            ),
            skipped_files=sum(1 for file in results if file.status == RepositoryFileParseStatus.SKIPPED),
            failed_files=sum(1 for file in results if file.status == RepositoryFileParseStatus.FAILED),
        )

    def parse_file(self, repository_path: Path, file: RepositoryFile) -> ParsedRepositoryFile:
        if file.is_binary:
            return ParsedRepositoryFile(
                repository_file_id=file.id,
                path=file.path,
                language=file.language,
                parser=None,
                status=RepositoryFileParseStatus.SKIPPED,
                error_message="Binary files are not parsed.",
            )

        extension = (file.extension or "").lower().removeprefix(".")
        if extension not in SUPPORTED_GRAMMARS:
            return ParsedRepositoryFile(
                repository_file_id=file.id,
                path=file.path,
                language=file.language,
                parser=None,
                status=RepositoryFileParseStatus.UNSUPPORTED,
                error_message="No Tree-sitter grammar is configured for this file.",
            )

        parser_name, parser = self._get_parser(extension)
        file_path = repository_path / file.path
        parsed_at = datetime.now(UTC)

        try:
            source = file_path.read_bytes()
            tree = parser.parse(source)
            root_node = tree.root_node
            error_count = self._count_error_nodes(root_node)
            status = (
                RepositoryFileParseStatus.SYNTAX_ERROR
                if root_node.has_error or error_count > 0
                else RepositoryFileParseStatus.PARSED
            )
            symbols = self._extract_symbols(root_node, source)
            imports = self._extract_imports(root_node, source)
            root_node_type = root_node.type
            has_error = root_node.has_error
            del root_node
            del tree
            return ParsedRepositoryFile(
                repository_file_id=file.id,
                path=file.path,
                language=file.language,
                parser=parser_name,
                status=status,
                root_node_type=root_node_type,
                has_error=has_error,
                error_count=error_count,
                symbols=symbols,
                imports=imports,
                parsed_at=parsed_at,
            )
        except Exception as exc:
            return ParsedRepositoryFile(
                repository_file_id=file.id,
                path=file.path,
                language=file.language,
                parser=parser_name,
                status=RepositoryFileParseStatus.FAILED,
                parsed_at=parsed_at,
                error_message=str(exc)[:2048],
            )

    async def replace_repository_parse_results(
        self,
        session: AsyncSession,
        repository_id: UUID,
        parse_result: RepositoryParseResult,
    ) -> None:
        await session.execute(
            delete(RepositoryFileParse).where(RepositoryFileParse.repository_id == repository_id)
        )
        session.add_all(
            [
                RepositoryFileParse(
                    repository_id=repository_id,
                    repository_file_id=file.repository_file_id,
                    path=file.path,
                    language=file.language,
                    parser=file.parser,
                    status=file.status.value,
                    root_node_type=file.root_node_type,
                    has_error=file.has_error,
                    error_count=file.error_count,
                    symbol_count=file.symbol_count,
                    import_count=file.import_count,
                    symbols=file.symbols,
                    imports=file.imports,
                    parsed_at=file.parsed_at,
                    error_message=file.error_message,
                )
                for file in parse_result.files
            ]
        )

    def _get_parser(self, extension: str) -> tuple[str, Parser]:
        if extension not in self._parsers:
            parser_name, language_factory = SUPPORTED_GRAMMARS[extension]
            self._parsers[extension] = (parser_name, Parser(language_factory()))
        return self._parsers[extension]

    def _extract_symbols(self, root_node: Node, source: bytes) -> list[dict]:
        symbols: list[dict] = []
        for node in self._walk(root_node):
            kind = SYMBOL_NODE_TYPES.get(node.type)
            name_node = node.child_by_field_name("name")
            if kind is None or name_node is None:
                if node.type == "variable_declarator":
                    name_node = node.child_by_field_name("name")
                    kind = "function" if self._has_function_value(node) else self._variable_kind(node)
                else:
                    continue

            name = self._node_text(name_node, source)
            if not name:
                continue

            symbols.append(
                {
                    "name": name,
                    "kind": kind,
                    "start_line": self._line_number_for_byte(source, node.start_byte),
                    "end_line": self._line_number_for_byte(source, node.end_byte),
                    "signature": self._symbol_signature(node, source),
                }
            )
        return symbols

    def _extract_imports(self, root_node: Node, source: bytes) -> list[dict]:
        imports: list[dict] = []
        for node in self._walk(root_node):
            if node.type not in IMPORT_NODE_TYPES:
                continue
            imports.append(
                {
                    "statement": self._node_text(node, source),
                    "source": self._import_source(node, source),
                    "items": self._import_items(node, source),
                    "start_line": self._line_number_for_byte(source, node.start_byte),
                    "end_line": self._line_number_for_byte(source, node.end_byte),
                }
            )
        return imports

    def _count_error_nodes(self, root_node: Node) -> int:
        error_nodes = sum(
            1
            for node in self._walk(root_node)
            if node.type == "ERROR" or node.is_error or node.is_missing
        )
        return max(1, error_nodes) if root_node.has_error else error_nodes

    def _walk(self, root_node: Node):
        stack = [root_node]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def _node_text(self, node: Node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace").strip()

    def _line_number_for_byte(self, source: bytes, byte_offset: int) -> int:
        return source.count(b"\n", 0, max(byte_offset, 0)) + 1

    def _has_function_value(self, node: Node) -> bool:
        value_node = node.child_by_field_name("value")
        return value_node is not None and value_node.type in {
            "arrow_function",
            "function_expression",
        }

    def _variable_kind(self, node: Node) -> str:
        parent = node.parent
        if parent is None or parent.type != "lexical_declaration":
            return "variable"
        first_child = parent.children[0] if parent.children else None
        if first_child is None:
            return "variable"
        return "constant" if first_child.type == "const" else "variable"

    def _symbol_signature(self, node: Node, source: bytes) -> str:
        text = self._node_text(node, source)
        first_line = text.splitlines()[0] if text else ""
        if "{" in first_line:
            first_line = first_line.split("{", 1)[0].strip()
        if ":" in first_line and node.type == "class_definition":
            first_line = first_line.split(":", 1)[0].strip()
        return first_line[:500]

    def _import_source(self, node: Node, source: bytes) -> str | None:
        if node.type == "import_from_statement":
            module_name = node.child_by_field_name("module_name")
            if module_name is not None:
                return self._node_text(module_name, source)

        for child in node.children:
            if child.type == "string":
                return self._node_text(child, source).strip("\"'")
        text = self._node_text(node, source)
        if text.startswith("import "):
            return text.split()[1].split(".", 1)[0]
        return None

    def _import_items(self, node: Node, source: bytes) -> list[str]:
        items: list[str] = []
        for child in self._walk(node):
            if child.type in {"identifier", "dotted_name"}:
                value = self._node_text(child, source)
                if value and value not in items:
                    items.append(value)
            elif child.type == "named_imports":
                for named_child in child.children:
                    if named_child.type == "import_specifier":
                        value = self._node_text(named_child, source)
                        if value and value not in items:
                            items.append(value)
        return items

    async def _ensure_repository_owner(
        self,
        session: AsyncSession,
        repository_id: UUID,
        owner_id: UUID,
    ) -> None:
        result = await session.execute(
            select(Repository.id).where(
                Repository.id == repository_id,
                Repository.owner_id == owner_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise RepositoryNotFoundError
