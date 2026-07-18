from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.extractors.config import ConfigurationKnowledgeExtractor
from app.modules.knowledge.extractors.documentation import DocumentationKnowledgeExtractor
from app.modules.knowledge.extractors.schema import PrismaSchemaKnowledgeExtractor
from app.modules.knowledge.router import list_repository_knowledge_items
from app.modules.knowledge.schemas import (
    RepositoryKnowledgeItemListResponse,
    RepositoryKnowledgeItemRead,
)
from app.modules.knowledge.service import (
    KnowledgeExtractionContext,
    RepositoryKnowledgeExtractionResult,
    RepositoryKnowledgeServiceImpl,
)
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


def test_knowledge_service_extracts_source_items_from_parse_results(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text(
        "import express from 'express';\n"
        "interface User { id: string }\n"
        "const router = express.Router();\n"
        "export function build() { return router }\n",
        encoding="utf-8",
    )
    file = make_file("src/app.ts", "ts", "TypeScript")
    parse_result = RepositoryParserServiceImpl().parse_repository(tmp_path, [file])

    result = RepositoryKnowledgeServiceImpl().extract_repository(
        KnowledgeExtractionContext(
            repository_id=REPOSITORY_ID,
            repository_path=tmp_path,
            files=[file],
            parse_result=parse_result,
        )
    )

    source_items = [
        item for item in result.items if item.source_type == RepositoryKnowledgeSourceType.SOURCE_CODE
    ]
    assert {item.item_type for item in source_items} == {"source_file", "symbol", "import"}
    assert any(item.name == "User" and item.data["kind"] == "interface" for item in source_items)
    assert any(item.name == "router" and item.data["kind"] == "constant" for item in source_items)
    assert any(item.item_type == "import" and item.data["source"] == "express" for item in source_items)


def test_documentation_extractor_extracts_markdown_structure(tmp_path) -> None:
    readme = make_file("README.md", "md", "Markdown")
    (tmp_path / "README.md").write_text(
        "---\ntitle: Project Guide\n---\n"
        "# Overview\n"
        "See [API](docs/API.md).\n\n"
        "```bash\nnpm test\n```\n\n"
        "## Install\nRun setup.\n",
        encoding="utf-8",
    )

    items = DocumentationKnowledgeExtractor().extract(
        KnowledgeExtractionContext(REPOSITORY_ID, tmp_path, [readme])
    )

    document = next(item for item in items if item.item_type == "document")
    sections = [item for item in items if item.item_type == "document_section"]
    assert document.name == "Project Guide"
    assert document.data["heading_count"] == 2
    assert document.data["link_count"] == 1
    assert document.data["code_block_count"] == 1
    assert [section.name for section in sections] == ["Overview", "Install"]


def test_documentation_extractor_handles_unlabelled_code_fences(tmp_path) -> None:
    readme = make_file("README.md", "md", "Markdown")
    (tmp_path / "README.md").write_text("# Guide\n```\nplain text\n```\n", encoding="utf-8")

    items = DocumentationKnowledgeExtractor().extract(
        KnowledgeExtractionContext(REPOSITORY_ID, tmp_path, [readme])
    )

    document = next(item for item in items if item.item_type == "document")
    assert document.data["code_blocks"] == [{"language": None, "start_line": 2, "end_line": 4}]


def test_prisma_extractor_extracts_models_relations_enums_and_constraints(tmp_path) -> None:
    prisma_dir = tmp_path / "prisma"
    prisma_dir.mkdir()
    schema = make_file("prisma/schema.prisma", "prisma", None)
    (prisma_dir / "schema.prisma").write_text(
        "model User {\n"
        "  id String @id @default(cuid())\n"
        "  posts Post[]\n"
        "  @@unique([id])\n"
        "}\n\n"
        "model Post {\n"
        "  id String @id\n"
        "  user User @relation(fields: [userId], references: [id])\n"
        "  userId String\n"
        "  @@index([userId])\n"
        "}\n\n"
        "enum Role {\n  ADMIN\n  USER\n}\n",
        encoding="utf-8",
    )

    items = PrismaSchemaKnowledgeExtractor().extract(
        KnowledgeExtractionContext(REPOSITORY_ID, tmp_path, [schema])
    )

    user = next(item for item in items if item.item_type == "prisma_model" and item.name == "User")
    post = next(item for item in items if item.item_type == "prisma_model" and item.name == "Post")
    role = next(item for item in items if item.item_type == "prisma_enum")
    assert user.data["constraints"] == ["@@unique([id])"]
    assert post.data["relations"][0]["name"] == "user"
    assert post.data["indexes"] == ["@@index([userId])"]
    assert role.data["values"] == ["ADMIN", "USER"]


def test_configuration_extractor_extracts_project_runtime_and_dependencies(tmp_path) -> None:
    package = make_file("package.json", "json", "JSON")
    requirements = make_file("requirements.txt", "txt", None)
    dockerfile = make_file("Dockerfile", None, "Dockerfile")
    compose = make_file("docker-compose.yml", "yml", "YAML")
    (tmp_path / "package.json").write_text(
        '{"name":"web","scripts":{"dev":"vite"},"dependencies":{"react":"latest","vite":"latest","express":"latest"}}',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("fastapi==0.116.1\npytest==8.4.1\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM node:22\nEXPOSE 3000\nCMD npm run dev\n", encoding="utf-8")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  api:\n    build: .\n    ports:\n      - \"8000:8000\"\n",
        encoding="utf-8",
    )

    items = ConfigurationKnowledgeExtractor().extract(
        KnowledgeExtractionContext(REPOSITORY_ID, tmp_path, [package, requirements, dockerfile, compose])
    )

    package_item = next(item for item in items if item.item_type == "package_manifest")
    requirements_item = next(item for item in items if item.item_type == "python_requirements")
    docker_item = next(item for item in items if item.item_type == "dockerfile")
    compose_item = next(item for item in items if item.item_type == "compose_config")
    assert package_item.data["frameworks"] == ["React", "Vite", "Express"]
    assert requirements_item.data["frameworks"] == ["FastAPI"]
    assert docker_item.data["runtime"] == ["Node.js"]
    assert compose_item.data["services"][0]["name"] == "api"


class FakeKnowledgeSession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added_all = []

    async def execute(self, statement):
        del statement
        self.execute_calls += 1

    def add_all(self, items):
        self.added_all.extend(items)


def test_knowledge_service_persists_items() -> None:
    session = FakeKnowledgeSession()
    timestamp = datetime.now(UTC)
    extraction_result = RepositoryKnowledgeExtractionResult(
        items=[
            SimpleNamespace(
                repository_file_id=None,
                path="README.md",
                source_type=RepositoryKnowledgeSourceType.DOCUMENTATION,
                item_type="document",
                name="README",
                extractor="documentation",
                data={"title": "README"},
                extracted_at=timestamp,
            )
        ]
    )

    asyncio.run(
        RepositoryKnowledgeServiceImpl().replace_repository_knowledge(
            session,
            REPOSITORY_ID,
            extraction_result,
        )
    )

    assert session.execute_calls == 1
    assert len(session.added_all) == 1
    assert session.added_all[0].source_type == "documentation"
    assert session.added_all[0].item_type == "document"


class FakeKnowledgeEndpointService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_args = None

    async def list_repository_knowledge_items(
        self,
        session,
        repository_id,
        owner_id,
        page,
        page_size,
        source_type=None,
        item_type=None,
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
            source_type,
            item_type,
            path_prefix,
        )
        timestamp = datetime.now(UTC)
        return RepositoryKnowledgeItemListResponse(
            knowledge_items=[
                RepositoryKnowledgeItemRead(
                    id=uuid4(),
                    repository_id=REPOSITORY_ID,
                    repository_file_id=None,
                    path="README.md",
                    source_type="documentation",
                    item_type="document",
                    name="README",
                    extractor="documentation",
                    data={"title": "README"},
                    extracted_at=timestamp,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ],
            page=page,
            page_size=page_size,
            has_next_page=False,
        )


def test_knowledge_endpoint_supports_filters() -> None:
    service = FakeKnowledgeEndpointService()

    response = asyncio.run(
        list_repository_knowledge_items(
            REPOSITORY_ID,
            page=2,
            page_size=25,
            source_type="documentation",
            item_type="document",
            path_prefix="README",
            session=object(),
            service=service,
            current_user=SimpleNamespace(id=OWNER_ID),
        )
    )

    assert response.knowledge_items[0].name == "README"
    assert service.requested_args == (
        REPOSITORY_ID,
        OWNER_ID,
        2,
        25,
        "documentation",
        "document",
        "README",
    )


def test_knowledge_endpoint_enforces_ownership() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            list_repository_knowledge_items(
                REPOSITORY_ID,
                session=object(),
                service=FakeKnowledgeEndpointService(RepositoryNotFoundError()),
                current_user=SimpleNamespace(id=OWNER_ID),
            )
        )

    assert exc.value.status_code == 404
