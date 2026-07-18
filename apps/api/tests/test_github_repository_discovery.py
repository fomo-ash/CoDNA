from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router
from app.db.dependencies import get_db_session
from app.modules.auth.dependencies import get_current_user_record
from app.modules.github.dependencies import get_github_service
from app.modules.github.schemas import GitHubRepository, GitHubRepositoryListResponse
from app.modules.github.service import (
    GitHubIntegrationError,
    GitHubRepositoryNotFoundError,
)
from app.modules.repositories.dependencies import get_repository_service
from app.modules.repositories.enums import RepositoryStatus
from app.modules.repositories.schemas import RepositoryRead
from app.modules.repositories.service import RepositoryAlreadyExistsError


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")


def make_github_repository() -> GitHubRepository:
    return GitHubRepository(
        github_id="12345",
        name="repo",
        full_name="octo/repo",
        default_branch="main",
        clone_url="https://github.com/octo/repo.git",
        visibility="private",
        private=True,
    )


def make_repository_read() -> RepositoryRead:
    timestamp = datetime.now(UTC)
    return RepositoryRead(
        id=uuid4(),
        owner_id=OWNER_ID,
        github_id="12345",
        name="repo",
        full_name="octo/repo",
        default_branch="main",
        clone_url="https://github.com/octo/repo.git",
        visibility="private",
        status=RepositoryStatus.REGISTERED,
        last_cloned_at=None,
        last_indexed_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeGitHubService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_identifier: dict[str, str | None] | None = None

    async def get_profile(self, user):
        del user
        if self.error:
            raise self.error
        raise AssertionError("profile was not expected in this test")

    async def list_repositories(self, user, **params):
        del user
        if self.error:
            raise self.error
        self.params = params
        return GitHubRepositoryListResponse(
            repositories=[make_github_repository()],
            page=params["page"],
            per_page=params["per_page"],
            has_next_page=True,
        )

    async def get_repository(self, user, *, github_id=None, full_name=None):
        del user
        self.requested_identifier = {"github_id": github_id, "full_name": full_name}
        if self.error:
            raise self.error
        return make_github_repository()


class FakeRepositoryService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.created_repository = None

    async def list_repositories(self, session, owner_id):
        del session, owner_id
        return []

    async def create_repository(self, session, owner_id, github_repository):
        del session, owner_id
        if self.error:
            raise self.error
        self.created_repository = github_repository
        return make_repository_read()

    async def get_repository(self, session, repository_id, owner_id):
        del session, repository_id, owner_id
        return make_repository_read()


def make_app(
    github_service: FakeGitHubService,
    repository_service: FakeRepositoryService | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    user = SimpleNamespace(id=OWNER_ID, github_access_token="github-token")

    async def fake_session():
        yield object()

    app.dependency_overrides[get_current_user_record] = lambda: user
    app.dependency_overrides[get_github_service] = lambda: github_service
    app.dependency_overrides[get_repository_service] = lambda: repository_service or FakeRepositoryService()
    app.dependency_overrides[get_db_session] = fake_session
    return app


def test_unauthorized_requests_are_rejected() -> None:
    app = FastAPI()
    app.include_router(api_router)

    with TestClient(app) as client:
        response = client.get("/api/v1/github/repositories")

    assert response.status_code == 401


def test_successful_repository_listing_supports_pagination() -> None:
    github_service = FakeGitHubService()
    app = make_app(github_service)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/github/repositories",
            params={"visibility": "private", "sort": "pushed", "page": 2, "per_page": 10},
        )

    assert response.status_code == 200
    assert response.json()["repositories"][0]["full_name"] == "octo/repo"
    assert response.json()["has_next_page"] is True
    assert github_service.params == {
        "visibility": "private",
        "sort": "pushed",
        "page": 2,
        "per_page": 10,
    }


def test_repository_import_uses_github_metadata() -> None:
    github_service = FakeGitHubService()
    repository_service = FakeRepositoryService()
    app = make_app(github_service, repository_service)

    with TestClient(app) as client:
        response = client.post("/api/v1/repositories", json={"full_name": "octo/repo"})

    assert response.status_code == 201
    assert github_service.requested_identifier == {"github_id": None, "full_name": "octo/repo"}
    assert repository_service.created_repository == make_github_repository()


def test_repository_not_found_is_returned_as_404() -> None:
    app = make_app(FakeGitHubService(GitHubRepositoryNotFoundError()))

    with TestClient(app) as client:
        response = client.post("/api/v1/repositories", json={"github_id": "404"})

    assert response.status_code == 404


def test_duplicate_repository_registration_is_returned_as_409() -> None:
    app = make_app(FakeGitHubService(), FakeRepositoryService(RepositoryAlreadyExistsError()))

    with TestClient(app) as client:
        response = client.post("/api/v1/repositories", json={"github_id": "12345"})

    assert response.status_code == 409


def test_github_api_failure_is_returned_as_502() -> None:
    app = make_app(FakeGitHubService(GitHubIntegrationError()))

    with TestClient(app) as client:
        response = client.get("/api/v1/github/repositories")

    assert response.status_code == 502


def test_repository_import_rejects_frontend_metadata() -> None:
    app = make_app(FakeGitHubService())

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/repositories",
            json={"full_name": "octo/repo", "status": "ready"},
        )

    assert response.status_code == 422
