from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings


class GitHubAPIError(Exception):
    def __init__(self, status_code: int | None, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class GitHubClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def api_base_url(self) -> str:
        return self.settings.github_api_url or "https://api.github.com"

    @property
    def token_url(self) -> str:
        return self.settings.github_token_url or "https://github.com/login/oauth/access_token"

    @property
    def user_url(self) -> str:
        return self.settings.github_user_url or "https://api.github.com/user"

    @property
    def repositories_url(self) -> str:
        return self.settings.github_repositories_url or "https://api.github.com/user/repos"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        response = await self._request(
            "POST",
            self.token_url,
            headers={"Accept": "application/json"},
            data={
                "client_id": self.settings.github_client_id,
                "client_secret": self.settings.github_client_secret,
                "code": code,
                "redirect_uri": self.settings.github_callback_url,
            },
        )
        return self._json(response)

    async def get_me(self, access_token: str) -> dict[str, Any]:
        response = await self._request("GET", self.user_url, access_token=access_token)
        return self._json(response)

    async def list_repositories(
        self,
        access_token: str,
        *,
        visibility: str,
        sort: str,
        page: int,
        per_page: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        response = await self._request(
            "GET",
            self.repositories_url,
            access_token=access_token,
            params={
                "visibility": visibility,
                "sort": sort,
                "page": page,
                "per_page": per_page,
            },
        )
        return self._json(response), 'rel="next"' in response.headers.get("link", "")

    async def get_repository(
        self,
        access_token: str,
        *,
        github_id: str | None = None,
        full_name: str | None = None,
    ) -> dict[str, Any]:
        if github_id is not None:
            url = f"{self.api_base_url}/repositories/{quote(github_id, safe='')}"
        else:
            url = f"{self.api_base_url}/repos/{quote(full_name or '', safe='/')}"
        response = await self._request("GET", url, access_token=access_token)
        return self._json(response)

    async def list_repository_history(
        self,
        access_token: str,
        *,
        full_name: str,
        artifact_type: str,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        endpoint = {
            "commit": "commits",
            "pull_request": "pulls",
            "issue": "issues",
        }[artifact_type]
        response = await self._request(
            "GET",
            f"{self.api_base_url}/repos/{quote(full_name, safe='/')}/{endpoint}",
            access_token=access_token,
            params={"state": "all", "per_page": per_page},
        )
        payload = self._json(response)
        return payload if isinstance(payload, list) else []

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any] | list[dict[str, Any]]:
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError(response.status_code, "GitHub API response was invalid.") from exc

    async def _request(
        self,
        method: str,
        url: str | None,
        *,
        access_token: str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int] | None = None,
        data: dict[str, str | None] | None = None,
    ) -> httpx.Response:
        if not url:
            raise GitHubAPIError(None, "GitHub integration is not configured.")

        request_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CoDNA-App/1.0",
        }
        if access_token:
            request_headers["Authorization"] = f"Bearer {access_token}"
        if headers:
            request_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    data=data,
                )
        except httpx.RequestError as exc:
            raise GitHubAPIError(None, "GitHub API request failed.") from exc

        if response.is_error:
            raise GitHubAPIError(response.status_code, "GitHub API returned an error.")
        return response
