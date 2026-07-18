from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.modules.parsing.enums import RepositoryFileParseStatus
from app.modules.parsing.router import list_repository_parse_results
from app.modules.parsing.schemas import RepositoryFileParseListResponse, RepositoryFileParseRead
from app.modules.parsing.service import RepositoryParserServiceImpl
from app.modules.repositories.service import RepositoryNotFoundError


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")


def make_file(path: str, extension: str | None, language: str | None, is_binary: bool = False):
    return SimpleNamespace(
        id=uuid4(),
        repository_id=REPOSITORY_ID,
        path=path,
        filename=path.rsplit("/", 1)[-1],
        extension=extension,
        language=language,
        is_binary=is_binary,
    )


def test_tree_sitter_parser_extracts_python_symbols_and_imports(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "import os\n\nclass Greeter:\n    def hello(self):\n        return os.getcwd()\n\n"
        "def build():\n    return Greeter()\n",
        encoding="utf-8",
    )

    result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [make_file("src/app.py", "py", "Python")],
    )

    assert result.parsed_files == 1
    parsed_file = result.files[0]
    assert parsed_file.status == RepositoryFileParseStatus.PARSED
    assert parsed_file.root_node_type == "module"
    assert parsed_file.error_count == 0
    assert [item["name"] for item in parsed_file.symbols] == ["Greeter", "hello", "build"]
    assert parsed_file.symbols[0]["kind"] == "class"
    assert parsed_file.imports == [
        {
            "statement": "import os",
            "source": "os",
            "items": ["os"],
            "start_line": 1,
            "end_line": 1,
        }
    ]


def test_tree_sitter_parser_extracts_typescript_symbols_and_imports(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text(
        "import thing from './thing';\n"
        "export class Service { run(): number { return 1 } }\n"
        "const build = () => new Service();\n",
        encoding="utf-8",
    )

    result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [make_file("src/app.ts", "ts", "TypeScript")],
    )

    parsed_file = result.files[0]
    assert parsed_file.status == RepositoryFileParseStatus.PARSED
    assert parsed_file.root_node_type == "program"
    assert [item["name"] for item in parsed_file.symbols] == ["Service", "run", "build"]
    assert [item["kind"] for item in parsed_file.symbols] == ["class", "method", "function"]
    assert parsed_file.imports[0]["statement"] == "import thing from './thing';"


def test_tree_sitter_parser_extracts_typescript_types_enums_and_constants(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "domain.ts").write_text(
        "interface User { id: string }\n"
        "type UserId = string;\n"
        "enum Role { Admin }\n"
        "const schema = z.object({ id: z.string() });\n",
        encoding="utf-8",
    )

    result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [make_file("src/domain.ts", "ts", "TypeScript")],
    )

    parsed_file = result.files[0]
    assert [item["name"] for item in parsed_file.symbols] == ["User", "UserId", "Role", "schema"]
    assert [item["kind"] for item in parsed_file.symbols] == [
        "interface",
        "type",
        "enum",
        "constant",
    ]


def test_tree_sitter_parser_records_syntax_errors_without_failing_repository(tmp_path) -> None:
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [make_file("broken.py", "py", "Python")],
    )

    assert result.syntax_error_files == 1
    assert result.files[0].status == RepositoryFileParseStatus.SYNTAX_ERROR
    assert result.files[0].has_error is True
    assert result.files[0].error_count > 0


def test_tree_sitter_parser_marks_binary_and_unsupported_files(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"hello\0world")

    result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [
            make_file("README.md", "md", "Markdown"),
            make_file("data.bin", "bin", None, is_binary=True),
        ],
    )

    assert [file.status for file in result.files] == [
        RepositoryFileParseStatus.UNSUPPORTED,
        RepositoryFileParseStatus.SKIPPED,
    ]
    assert result.unsupported_files == 1
    assert result.skipped_files == 1


class FakeParseSession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added_all = []

    async def execute(self, statement):
        del statement
        self.execute_calls += 1

    def add_all(self, items):
        self.added_all.extend(items)


def test_parser_service_persists_parse_results(tmp_path) -> None:
    (tmp_path / "app.py").write_text("def build():\n    return 1\n", encoding="utf-8")
    parse_result = RepositoryParserServiceImpl().parse_repository(
        tmp_path,
        [make_file("app.py", "py", "Python")],
    )
    session = FakeParseSession()

    asyncio.run(
        RepositoryParserServiceImpl().replace_repository_parse_results(
            session,
            REPOSITORY_ID,
            parse_result,
        )
    )

    assert session.execute_calls == 1
    assert len(session.added_all) == 1
    assert session.added_all[0].path == "app.py"
    assert session.added_all[0].status == "parsed"
    assert session.added_all[0].symbol_count == 1


class FakeParserEndpointService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_args = None

    async def list_repository_parse_results(
        self,
        session,
        repository_id,
        owner_id,
        page,
        page_size,
        status=None,
        language=None,
        path_prefix=None,
    ):
        del session
        if self.error:
            raise self.error
        self.requested_args = (
            repository_id,
            owner_id,
            page,
            page_size,
            status,
            language,
            path_prefix,
        )
        timestamp = datetime.now(UTC)
        return RepositoryFileParseListResponse(
            parse_results=[
                RepositoryFileParseRead(
                    id=uuid4(),
                    repository_id=REPOSITORY_ID,
                    repository_file_id=uuid4(),
                    path="src/app.py",
                    language="Python",
                    parser="python",
                    status="parsed",
                    root_node_type="module",
                    has_error=False,
                    error_count=0,
                    symbol_count=1,
                    import_count=0,
                    symbols=[{"name": "build", "kind": "function", "start_line": 1, "end_line": 2}],
                    imports=[],
                    parsed_at=timestamp,
                    error_message=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ],
            page=page,
            page_size=page_size,
            has_next_page=False,
        )


def test_parse_results_endpoint_supports_filters() -> None:
    service = FakeParserEndpointService()

    response = asyncio.run(
        list_repository_parse_results(
            REPOSITORY_ID,
            page=2,
            page_size=25,
            status_filter="parsed",
            language="Python",
            path_prefix="src/",
            session=object(),
            service=service,
            current_user=SimpleNamespace(id=OWNER_ID),
        )
    )

    assert response.parse_results[0].path == "src/app.py"
    assert service.requested_args == (
        REPOSITORY_ID,
        OWNER_ID,
        2,
        25,
        "parsed",
        "Python",
        "src/",
    )


def test_parse_results_endpoint_enforces_ownership() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            list_repository_parse_results(
                REPOSITORY_ID,
                session=object(),
                service=FakeParserEndpointService(RepositoryNotFoundError()),
                current_user=SimpleNamespace(id=OWNER_ID),
            )
        )

    assert exc.value.status_code == 404
