from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.modules.chunks.builder import SemanticChunkBuilder
from app.modules.chunks.router import get_chunk, list_repository_chunks
from app.modules.chunks.schemas import RepositoryChunkListResponse, RepositoryChunkRead
from app.modules.chunks.service import RepositoryChunkNotFoundError


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")


def knowledge_item(path: str, source_type: str, item_type: str, data: dict, name: str | None = None):
    return SimpleNamespace(
        repository_file_id=uuid4(),
        path=path,
        source_type=source_type,
        item_type=item_type,
        data=data,
        name=name,
    )


def test_builder_groups_python_class_and_builds_top_level_function(tmp_path) -> None:
    (tmp_path / "environment.py").write_text(
        "import random\n\nclass StudentLifeEnv:\n    def step(self, action) -> int:\n        return 1\n\ndef run_episode():\n    return StudentLifeEnv()\n",
        encoding="utf-8",
    )
    source_file = knowledge_item(
        "environment.py", "source_code", "source_file", {"language": "Python", "parser": "python"}
    )
    class_item = knowledge_item(
        "environment.py", "source_code", "symbol",
        {"name": "StudentLifeEnv", "kind": "class", "start_line": 3, "end_line": 5, "stable_symbol_id": "environment.py::StudentLifeEnv", "is_exported": True},
        "StudentLifeEnv",
    )
    method_item = knowledge_item(
        "environment.py", "source_code", "symbol",
        {"name": "step", "kind": "function", "parent_symbol": "StudentLifeEnv", "start_line": 4, "end_line": 5, "signature": "def step(self, action) -> int:", "parameters": ["self", "action"], "return_type": "int"},
        "step",
    )
    function_item = knowledge_item(
        "environment.py", "source_code", "symbol",
        {"name": "run_episode", "kind": "function", "start_line": 7, "end_line": 8, "signature": "def run_episode():", "parameters": [], "is_exported": True},
        "run_episode",
    )
    import_item = knowledge_item(
        "environment.py", "source_code", "import", {"source": "random", "items": ["random"]}, "random"
    )

    chunks = SemanticChunkBuilder().build(
        tmp_path, [source_file, class_item, method_item, function_item, import_item], REPOSITORY_ID
    )

    assert [chunk.chunk_type for chunk in chunks] == ["class", "function"]
    class_chunk, function_chunk = chunks
    assert "class StudentLifeEnv" in class_chunk.content
    assert class_chunk.metadata["methods"][0]["name"] == "step"
    assert function_chunk.title == "run_episode"
    assert function_chunk.content == "def run_episode():\n    return StudentLifeEnv()"
    assert function_chunk.metadata["parser"] == "python"
    assert function_chunk.metadata["repository_id"] == str(REPOSITORY_ID)
    assert function_chunk.metadata["relationships"] == {
        "calls": [], "called_by": [], "imports": [], "imported_by": [],
        "inherits": [], "implements": [], "references": [], "exports": ["run_episode"],
    }


def test_builder_creates_markdown_section_prisma_and_configuration_chunks(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Install\nRun `npm install`.\n", encoding="utf-8")
    (tmp_path / "schema.prisma").write_text("model User {\n  id String @id\n}\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"web","scripts":{"dev":"vite"}}\n', encoding="utf-8")
    items = [
        knowledge_item("README.md", "documentation", "document_section", {"heading": {"title": "Install", "level": 1, "slug": "install"}, "start_line": 1, "end_line": 2}, "Install"),
        knowledge_item("schema.prisma", "database_schema", "prisma_model", {"name": "User", "start_line": 1, "end_line": 3, "fields": [{"name": "id"}], "relations": [], "indexes": [], "constraints": []}, "User"),
        knowledge_item("package.json", "configuration", "package_manifest", {"frameworks": ["Vite"], "runtime": {"node": None}, "dependencies": [], "scripts": {"dev": "vite"}}, "web"),
    ]

    chunks = SemanticChunkBuilder().build(tmp_path, items)

    assert {chunk.chunk_type for chunk in chunks} == {"documentation_section", "configuration", "prisma_model"}
    chunk_by_type = {chunk.chunk_type: chunk for chunk in chunks}
    documentation = chunk_by_type["documentation_section"]
    configuration = chunk_by_type["configuration"]
    prisma = chunk_by_type["prisma_model"]
    assert documentation.metadata["heading"] == "Install"
    assert documentation.metadata["section_depth"] == 1
    assert documentation.metadata["relationships"]["exports"] == []
    assert '"name":"web"' in configuration.content
    assert prisma.metadata["model_name"] == "User"
    assert prisma.metadata["enums"] == []
    assert prisma.content == "model User {\n  id String @id\n}"


def test_builder_resolves_repository_local_call_and_import_relationships(tmp_path) -> None:
    (tmp_path / "helpers.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (tmp_path / "worker.py").write_text("from helpers import run\n\ndef execute():\n    return run()\n", encoding="utf-8")
    items = [
        knowledge_item("helpers.py", "source_code", "source_file", {"language": "Python"}),
        knowledge_item("helpers.py", "source_code", "symbol", {"name": "run", "kind": "function", "start_line": 1, "end_line": 2, "stable_symbol_id": "helpers.py::run", "calls": [], "references": [], "is_exported": True}, "run"),
        knowledge_item("worker.py", "source_code", "source_file", {"language": "Python"}),
        knowledge_item("worker.py", "source_code", "import", {"source": "helpers", "items": ["helpers", "run"]}, "helpers"),
        knowledge_item("worker.py", "source_code", "symbol", {"name": "execute", "kind": "function", "start_line": 3, "end_line": 4, "stable_symbol_id": "worker.py::execute", "calls": ["run"], "references": [], "is_exported": True}, "execute"),
    ]

    chunks = SemanticChunkBuilder().build(tmp_path, items)
    chunk_by_title = {chunk.title: chunk for chunk in chunks}

    execute = chunk_by_title["execute"]
    run = chunk_by_title["run"]
    assert execute.metadata["relationships"]["calls"] == [
        {"symbol": "run", "path": "helpers.py", "stable_symbol_id": "helpers.py::run"}
    ]
    assert execute.metadata["relationships"]["imports"] == [
        {"symbol": "run", "path": "helpers.py", "stable_symbol_id": "helpers.py::run"}
    ]
    assert execute.metadata["file_imports"] == [{"source": "helpers", "items": ["helpers", "run"]}]
    assert execute.metadata["used_imports"] == ["run"]
    assert run.metadata["relationships"]["called_by"] == [
        {"symbol": "worker.py::execute", "path": "worker.py"}
    ]


def test_builder_resolves_multilevel_typescript_relative_imports(tmp_path) -> None:
    api_path = tmp_path / "apps/web/lib/api.ts"
    page_path = tmp_path / "apps/web/app/repositories/[id]/search/page.tsx"
    api_path.parent.mkdir(parents=True)
    page_path.parent.mkdir(parents=True)
    api_path.write_text("export function api() { return 'ok'; }\n", encoding="utf-8")
    page_path.write_text(
        "import { api } from '../../../../lib/api';\nexport function search() { return api(); }\n",
        encoding="utf-8",
    )
    items = [
        knowledge_item("apps/web/lib/api.ts", "source_code", "source_file", {"language": "TypeScript"}),
        knowledge_item("apps/web/lib/api.ts", "source_code", "symbol", {
            "name": "api", "kind": "function", "start_line": 1, "end_line": 1,
            "stable_symbol_id": "apps/web/lib/api.ts::api", "calls": [], "references": [], "is_exported": True,
        }, "api"),
        knowledge_item("apps/web/app/repositories/[id]/search/page.tsx", "source_code", "source_file", {"language": "TSX"}),
        knowledge_item("apps/web/app/repositories/[id]/search/page.tsx", "source_code", "import", {
            "source": "../../../../lib/api", "items": ["api"],
        }, "api"),
        knowledge_item("apps/web/app/repositories/[id]/search/page.tsx", "source_code", "symbol", {
            "name": "search", "kind": "function", "start_line": 2, "end_line": 2,
            "stable_symbol_id": "apps/web/app/repositories/[id]/search/page.tsx::search", "calls": ["api"], "references": [], "is_exported": True,
        }, "search"),
    ]

    chunks = SemanticChunkBuilder().build(tmp_path, items)
    chunk_by_title = {chunk.title: chunk for chunk in chunks}

    assert chunk_by_title["search"].metadata["relationships"]["imports"] == [
        {"symbol": "api", "path": "apps/web/lib/api.ts", "stable_symbol_id": "apps/web/lib/api.ts::api"}
    ]
    assert chunk_by_title["api"].metadata["relationships"]["imported_by"] == [
        {"path": "apps/web/app/repositories/[id]/search/page.tsx"}
    ]


def test_builder_creates_constant_chunks_and_resolves_references(tmp_path) -> None:
    (tmp_path / "settings.py").write_text("LIMIT = 3\n\ndef get_limit():\n    return LIMIT\n", encoding="utf-8")
    items = [
        knowledge_item("settings.py", "source_code", "source_file", {"language": "Python"}),
        knowledge_item("settings.py", "source_code", "symbol", {"name": "LIMIT", "kind": "constant", "start_line": 1, "end_line": 1, "stable_symbol_id": "settings.py::LIMIT", "is_exported": True}, "LIMIT"),
        knowledge_item("settings.py", "source_code", "symbol", {"name": "get_limit", "kind": "function", "start_line": 3, "end_line": 4, "stable_symbol_id": "settings.py::get_limit", "calls": [], "references": ["LIMIT"], "is_exported": True}, "get_limit"),
    ]

    chunks = SemanticChunkBuilder().build(tmp_path, items)
    chunk_by_type = {chunk.chunk_type: chunk for chunk in chunks}

    assert chunk_by_type["constants"].metadata["symbols"][0]["stable_symbol_id"] == "settings.py::LIMIT"
    assert chunk_by_type["function"].metadata["relationships"]["references"] == [
        {"symbol": "LIMIT", "path": "settings.py", "stable_symbol_id": "settings.py::LIMIT"}
    ]


def test_builder_does_not_resolve_unimported_references_to_another_file(tmp_path) -> None:
    (tmp_path / "environment.py").write_text("def use_tasks():\n    return tasks\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def tasks():\n    return {}\n", encoding="utf-8")
    items = [
        knowledge_item("environment.py", "source_code", "source_file", {"language": "Python"}),
        knowledge_item("environment.py", "source_code", "symbol", {
            "name": "use_tasks", "kind": "function", "start_line": 1, "end_line": 2,
            "stable_symbol_id": "environment.py::use_tasks", "calls": [], "references": ["tasks"],
            "is_exported": True,
        }, "use_tasks"),
        knowledge_item("main.py", "source_code", "source_file", {"language": "Python"}),
        knowledge_item("main.py", "source_code", "symbol", {
            "name": "tasks", "kind": "function", "start_line": 1, "end_line": 2,
            "stable_symbol_id": "main.py::tasks", "calls": [], "references": [], "is_exported": True,
        }, "tasks"),
    ]

    chunks = SemanticChunkBuilder().build(tmp_path, items)
    use_tasks = next(chunk for chunk in chunks if chunk.title == "use_tasks")

    assert use_tasks.metadata["relationships"]["references"] == [{"symbol": "tasks"}]


class FakeChunkEndpointService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.args = None

    async def list_repository_chunks(
        self, session, repository_id, owner_id, page, page_size, source_type=None, chunk_type=None, search=None,
    ):
        del session
        if self.error:
            raise self.error
        self.args = (repository_id, owner_id, page, page_size, source_type, chunk_type, search)
        return RepositoryChunkListResponse(chunks=[self._chunk()], page=page, page_size=page_size, has_next_page=False)

    async def get_chunk(self, session, chunk_id, owner_id):
        del session
        if self.error:
            raise self.error
        self.args = (chunk_id, owner_id)
        return self._chunk(chunk_id)

    def _chunk(self, chunk_id=None) -> RepositoryChunkRead:
        timestamp = datetime.now(UTC)
        return RepositoryChunkRead(
            id=chunk_id or uuid4(), repository_id=REPOSITORY_ID, repository_file_id=None,
            path="README.md", chunk_type="documentation_section", source_type="documentation",
            title="Install", language="Markdown", content="# Install", start_line=1, end_line=1,
            metadata={"slug": "install"}, created_at=timestamp, updated_at=timestamp,
        )


def test_chunk_endpoints_filter_and_enforce_ownership() -> None:
    service = FakeChunkEndpointService()
    response = asyncio.run(list_repository_chunks(
        REPOSITORY_ID, page=2, page_size=20, source_type="documentation", chunk_type="documentation_section",
        search=None, session=object(), service=service, current_user=SimpleNamespace(id=OWNER_ID),
    ))
    assert response.chunks[0].title == "Install"
    assert service.args == (REPOSITORY_ID, OWNER_ID, 2, 20, "documentation", "documentation_section", None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_chunk(uuid4(), session=object(), service=FakeChunkEndpointService(RepositoryChunkNotFoundError()), current_user=SimpleNamespace(id=OWNER_ID)))
    assert exc.value.status_code == 404
