from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.config import Settings
from app.db.models.user import User
from app.modules.github.client import GitHubAPIError, GitHubClient
from app.modules.github.schemas import (
    GitHubAccessTokenResponse,
    GitHubProfile,
    GitHubProfileResponse,
    GitHubRepository,
    GitHubRepositoryListResponse,
)


class GitHubAuthorizationRequiredError(Exception):
    pass


class GitHubRepositoryNotFoundError(Exception):
    pass


class GitHubIntegrationError(Exception):
    pass


class GitHubServiceImpl:
    def __init__(self, settings: Settings, client: GitHubClient | None = None) -> None:
        self.client = client or GitHubClient(settings)

    async def exchange_code(self, code: str) -> GitHubAccessTokenResponse:
        try:
            return GitHubAccessTokenResponse.model_validate(await self.client.exchange_code(code))
        except (GitHubAPIError, ValidationError) as exc:
            raise GitHubIntegrationError from exc

    async def get_profile(self, user: User) -> GitHubProfile:
        return await self.get_profile_for_token(self._get_access_token(user))

    async def get_profile_for_token(self, access_token: str) -> GitHubProfile:
        try:
            profile = GitHubProfileResponse.model_validate(await self.client.get_me(access_token))
        except (GitHubAPIError, ValidationError) as exc:
            self._raise_integration_error(exc)
        return GitHubProfile(
            github_id=str(profile.id),
            username=profile.login,
            email=profile.email,
            name=profile.name,
            avatar_url=profile.avatar_url,
        )

    async def list_repositories(
        self,
        user: User,
        *,
        visibility: str,
        sort: str,
        page: int,
        per_page: int,
    ) -> GitHubRepositoryListResponse:
        access_token = self._get_access_token(user)
        try:
            payload, has_next_page = await self.client.list_repositories(
                access_token,
                visibility=visibility,
                sort=sort,
                page=page,
                per_page=per_page,
            )
        except (GitHubAPIError, ValidationError) as exc:
            self._raise_integration_error(exc)

        return GitHubRepositoryListResponse(
            repositories=[self._to_repository(item) for item in payload],
            page=page,
            per_page=per_page,
            has_next_page=has_next_page,
        )

    async def get_repository(
        self,
        user: User,
        *,
        github_id: str | None = None,
        full_name: str | None = None,
    ) -> GitHubRepository:
        access_token = self._get_access_token(user)
        try:
            payload = await self.client.get_repository(
                access_token,
                github_id=github_id,
                full_name=full_name,
            )
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                raise GitHubRepositoryNotFoundError from exc
            self._raise_integration_error(exc)
        return self._to_repository(payload)

    @staticmethod
    def _get_access_token(user: User) -> str:
        if not user.github_access_token:
            raise GitHubAuthorizationRequiredError
        return user.github_access_token

    @staticmethod
    def _to_repository(payload: dict[str, Any]) -> GitHubRepository:
        private = bool(payload.get("private", False))
        visibility = payload.get("visibility") or ("private" if private else "public")
        try:
            return GitHubRepository(
                github_id=str(payload["id"]),
                name=payload["name"],
                full_name=payload["full_name"],
                default_branch=payload.get("default_branch"),
                clone_url=payload["clone_url"],
                visibility=visibility,
                private=private,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubIntegrationError from exc

    @staticmethod
    def _raise_integration_error(error: Exception) -> None:
        if getattr(error, "status_code", None) == 401:
            raise GitHubAuthorizationRequiredError from error
        raise GitHubIntegrationError from error
