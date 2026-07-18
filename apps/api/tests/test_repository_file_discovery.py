from __future__ import annotations

import asyncio
import inspect
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.params import Depends

from app.modules.auth.dependencies import get_current_user_record
from app.modules.files.discovery import RepositoryFileDiscoveryService
from app.modules.files.router import get_repository_stats, list_repository_files
from app.modules.files.schemas import RepositoryFileListResponse, RepositoryFileRead, RepositoryStatsRead
from app.modules.files.service import RepositoryFileServiceImpl
from app.modules.jobs.enums import JobStatus
from app.modules.repositories.enums import RepositoryStatus
from app.modules.repositories.service import RepositoryNotFoundError
from app.workers import tasks


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")
JOB_ID = UUID("00000000-0000-0000-0000-000000000003")


def test_repository_scan_discovers_files_hashes_languages_and_stats(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "src" / "app.ts").write_text("const value = 1;\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"hello\0world")

    result = RepositoryFileDiscoveryService(max_file_size_bytes=10 * 1024 * 1024).discover(tmp_path)

    assert [file.path for file in result.files] == [
        "README.md",
        "data.bin",
        "src/app.py",
        "src/app.ts",
    ]
    python_file = next(file for file in result.files if file.path == "src/app.py")
    assert python_file.filename == "app.py"
    assert python_file.extension == "py"
    assert python_file.language == "Python"
    assert python_file.sha256 == "03e693d9f2f687e0f40e36a8df7fcb4d1c22974012b7c2a55c000eb30f305824"
    assert python_file.is_binary is False

    binary_file = next(file for file in result.files if file.path == "data.bin")
    assert binary_file.language is None
    assert binary_file.is_binary is True

    assert result.stats.total_files == 4
    assert result.stats.source_files == 3
    assert result.stats.binary_files == 1
    assert result.stats.detected_languages == {"Markdown": 1, "Python": 1, "TypeScript": 1}


def test_repository_scan_applies_ignore_rules_and_file_size_limit(tmp_path) -> None:
    ignored_directories = [
        ".git",
        ".github",
        "node_modules",
        "dist",
        "build",
        ".next",
        "coverage",
        "__pycache__",
        "venv",
        ".venv",
        ".idea",
        ".vscode",
        "target",
        "vendor",
    ]
    for directory_name in ignored_directories:
        directory = tmp_path / directory_name
        directory.mkdir()
        (directory / "ignored.py").write_text("print('ignored')\n", encoding="utf-8")

    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    (tmp_path / "archive.zip").write_bytes(b"PK")
    (tmp_path / "large.py").write_text("x" * 32, encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=value\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("print('ok')\n", encoding="utf-8")

    result = RepositoryFileDiscoveryService(max_file_size_bytes=20).discover(tmp_path)

    assert [file.path for file in result.files] == ["src.py"]
    assert result.stats.total_files == 1
    assert result.stats.source_files == 1


def test_repository_scan_handles_empty_repository(tmp_path) -> None:
    result = RepositoryFileDiscoveryService().discover(tmp_path)

    assert result.files == []
    assert result.stats.total_files == 0
    assert result.stats.source_files == 0
    assert result.stats.binary_files == 0
    assert result.stats.total_size_bytes == 0
    assert result.stats.detected_languages == {}


class FakeRepositoryFileService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_args: tuple | None = None

    async def list_repository_files(
        self,
        session,
        repository_id,
        owner_id,
        page,
        page_size,
        language=None,
        extension=None,
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
            language,
            extension,
            path_prefix,
        )
        timestamp = datetime.now(UTC)
        return RepositoryFileListResponse(
            files=[
                RepositoryFileRead(
                    id=uuid4(),
                    repository_id=REPOSITORY_ID,
                    path="src/app.py",
                    filename="app.py",
                    extension="py",
                    language="Python",
                    size_bytes=15,
                    sha256="0" * 64,
                    is_binary=False,
                    discovered_at=timestamp,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            ],
            page=page,
            page_size=page_size,
            has_next_page=False,
        )

    async def get_repository_stats(self, session, repository_id, owner_id):
        del session
        if self.error:
            raise self.error
        return RepositoryStatsRead(
            repository_id=repository_id,
            total_files=1,
            source_files=1,
            binary_files=0,
            total_size_bytes=15,
            languages={"Python": 1},
            last_scan_at=datetime.now(UTC),
        )


def test_repository_files_endpoint_supports_pagination_and_filters() -> None:
    file_service = FakeRepositoryFileService()
    response = asyncio.run(
        list_repository_files(
            REPOSITORY_ID,
            page=2,
            page_size=50,
            language="Python",
            extension="py",
            path_prefix="src/",
            session=object(),
            service=file_service,
            current_user=SimpleNamespace(id=OWNER_ID),
        )
    )

    assert response.files[0].path == "src/app.py"
    assert response.page == 2
    assert response.page_size == 50
    assert file_service.requested_args == (
        REPOSITORY_ID,
        OWNER_ID,
        2,
        50,
        "Python",
        "py",
        "src/",
    )


def test_repository_stats_endpoint_returns_persisted_statistics() -> None:
    response = asyncio.run(
        get_repository_stats(
            REPOSITORY_ID,
            session=object(),
            service=FakeRepositoryFileService(),
            current_user=SimpleNamespace(id=OWNER_ID),
        )
    )

    assert response.repository_id == REPOSITORY_ID
    assert response.languages == {"Python": 1}


def test_repository_file_endpoints_enforce_ownership() -> None:
    file_service = FakeRepositoryFileService(RepositoryNotFoundError())

    with pytest.raises(HTTPException) as files_exc:
        asyncio.run(
            list_repository_files(
                REPOSITORY_ID,
                session=object(),
                service=file_service,
                current_user=SimpleNamespace(id=OWNER_ID),
            )
        )
    with pytest.raises(HTTPException) as stats_exc:
        asyncio.run(
            get_repository_stats(
                REPOSITORY_ID,
                session=object(),
                service=file_service,
                current_user=SimpleNamespace(id=OWNER_ID),
            )
        )

    assert files_exc.value.status_code == 404
    assert stats_exc.value.status_code == 404


def test_repository_file_handlers_require_authenticated_user_dependency() -> None:
    current_user_default = inspect.signature(list_repository_files).parameters["current_user"].default

    assert isinstance(current_user_default, Depends)
    assert current_user_default.dependency is get_current_user_record


class FakeExecuteResult:
    def __init__(self, scalar_value=None, rows=None) -> None:
        self.scalar_value = scalar_value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.rows)


class FakeInventorySession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added = []
        self.added_all = []

    async def execute(self, statement):
        del statement
        self.execute_calls += 1
        return FakeExecuteResult()

    def add(self, item):
        self.added.append(item)

    def add_all(self, items):
        self.added_all.extend(items)


def test_repository_file_service_persists_files_and_statistics(tmp_path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    discovery_result = RepositoryFileDiscoveryService().discover(tmp_path)
    session = FakeInventorySession()

    asyncio.run(
        RepositoryFileServiceImpl().replace_repository_inventory(
            session,
            REPOSITORY_ID,
            discovery_result,
        )
    )

    assert len(session.added_all) == 1
    assert session.added_all[0].path == "app.py"
    assert session.added_all[0].filename == "app.py"
    assert session.added_all[0].is_binary is False
    assert len(session.added) == 1
    assert session.added[0].total_files == 1
    assert session.added[0].detected_languages == {"Python": 1}


def test_repository_file_service_raises_when_repository_not_owned() -> None:
    session = FakeInventorySession()

    with pytest.raises(RepositoryNotFoundError):
        asyncio.run(
            RepositoryFileServiceImpl().list_repository_files(
                session,
                REPOSITORY_ID,
                OWNER_ID,
                1,
                50,
            )
        )


def test_worker_success_path_discovers_and_persists_inventory(monkeypatch, tmp_path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    timestamp = datetime.now(UTC)
    job = SimpleNamespace(id=JOB_ID, status=None, started_at=None, completed_at=None)
    repository = SimpleNamespace(
        id=REPOSITORY_ID,
        status=None,
        clone_url="https://github.com/octo/repo.git",
        default_branch="main",
        visibility="public",
        clone_path=None,
        last_cloned_at=None,
        last_indexed_at=None,
    )
    user = SimpleNamespace(github_access_token="token")
    persisted = {}

    async def fake_get_job_and_repository(session, job_id, repository_id):
        del session
        assert job_id == JOB_ID
        assert repository_id == REPOSITORY_ID
        return job, repository, user

    class FakeCloneService:
        def __init__(self, workspace_path) -> None:
            self.workspace_path = workspace_path

        async def clone_repository(self, target):
            assert target.repository_id == REPOSITORY_ID
            return SimpleNamespace(clone_path=tmp_path, cloned_at=timestamp)

    class FakeRepositoryFileService:
        async def replace_repository_inventory(self, session, repository_id, discovery_result):
            del session
            persisted["repository_id"] = repository_id
            persisted["result"] = discovery_result

    async def fake_to_thread(function, *args):
        return function(*args)

    async def fake_commit():
        return None

    @asynccontextmanager
    async def fake_worker_session_with_async_commit():
        yield SimpleNamespace(commit=fake_commit)

    monkeypatch.setattr(tasks, "worker_session", fake_worker_session_with_async_commit)
    monkeypatch.setattr(tasks, "_get_job_and_repository", fake_get_job_and_repository)
    monkeypatch.setattr(tasks, "RepositoryCloneService", FakeCloneService)
    monkeypatch.setattr(tasks, "RepositoryFileServiceImpl", FakeRepositoryFileService)
    monkeypatch.setattr(tasks.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        tasks,
        "get_settings",
        lambda: SimpleNamespace(
            repository_workspace_path=str(tmp_path.parent),
            repository_file_max_bytes=10 * 1024 * 1024,
            repository_file_discovery_limit=5000,
        ),
    )

    asyncio.run(tasks._run_repository_index(JOB_ID, REPOSITORY_ID))

    assert job.status == JobStatus.COMPLETED
    assert repository.status == RepositoryStatus.READY
    assert repository.last_indexed_at is not None
    assert persisted["repository_id"] == REPOSITORY_ID
    assert persisted["result"].stats.total_files == 1


def test_worker_failure_path_marks_job_and_repository_failed(monkeypatch, tmp_path) -> None:
    job = SimpleNamespace(id=JOB_ID, status=None, started_at=None, completed_at=None)
    repository = SimpleNamespace(
        id=REPOSITORY_ID,
        status=None,
        clone_url="https://github.com/octo/repo.git",
        default_branch="main",
        visibility="public",
    )
    marked_failed = {}

    async def fake_commit():
        return None

    @asynccontextmanager
    async def fake_worker_session():
        yield SimpleNamespace(commit=fake_commit)

    async def fake_get_job_and_repository(session, job_id, repository_id):
        del session, job_id, repository_id
        return job, repository, None

    class FailingCloneService:
        def __init__(self, workspace_path) -> None:
            self.workspace_path = workspace_path

        async def clone_repository(self, target):
            del target
            raise RuntimeError("clone failed")

    async def fake_mark_failed(job_id, repository_id, error_message):
        marked_failed["job_id"] = job_id
        marked_failed["repository_id"] = repository_id
        marked_failed["error_message"] = error_message

    monkeypatch.setattr(tasks, "worker_session", fake_worker_session)
    monkeypatch.setattr(tasks, "_get_job_and_repository", fake_get_job_and_repository)
    monkeypatch.setattr(tasks, "RepositoryCloneService", FailingCloneService)
    monkeypatch.setattr(tasks, "_mark_failed", fake_mark_failed)
    monkeypatch.setattr(
        tasks,
        "get_settings",
        lambda: SimpleNamespace(repository_workspace_path=str(tmp_path)),
    )

    with pytest.raises(RuntimeError, match="clone failed"):
        asyncio.run(tasks._run_repository_index(JOB_ID, REPOSITORY_ID))

    assert marked_failed == {
        "job_id": JOB_ID,
        "repository_id": REPOSITORY_ID,
        "error_message": "clone failed",
    }
