from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.user import User
from app.modules.auth.schemas import (
    AuthCallbackQuery,
    AuthTokenResponse,
    CurrentUser,
    GitHubAccessTokenResponse,
    GitHubUserProfile,
)
from app.modules.auth.utils.jwt import create_access_token, create_oauth_state_token, decode_oauth_state_token


class AuthServiceImpl:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_github_login_url(self) -> str:
        self._validate_github_settings()
        state = create_oauth_state_token(self.settings)
        params = urlencode(
            {
                "client_id": self.settings.github_client_id,
                "redirect_uri": self.settings.github_callback_url,
                "scope": self.settings.github_scope,
                "state": state,
            }
        )
        return f"{self.settings.github_authorize_url}?{params}"

    async def authenticate_with_github(
        self,
        session: AsyncSession,
        payload: AuthCallbackQuery,
    ) -> AuthTokenResponse:
        self._validate_github_settings()
        decode_oauth_state_token(self.settings, payload.state)

        token_response = await self._exchange_code_for_token(payload.code)
        github_user = await self._fetch_github_user(token_response.access_token)
        user = await self._upsert_user(session, github_user)

        access_token, expires_in = create_access_token(self.settings, str(user.id))
        return AuthTokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            user=CurrentUser.model_validate(user),
        )

    async def get_current_user(self, session: AsyncSession, user_id: str) -> CurrentUser:
        try:
            parsed_user_id = UUID(user_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            ) from exc

        result = await session.execute(select(User).where(User.id == parsed_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user not found.",
            )
        return CurrentUser.model_validate(user)

    def _validate_github_settings(self) -> None:
        required = {
            "github_client_id": self.settings.github_client_id,
            "github_client_secret": self.settings.github_client_secret,
            "github_callback_url": self.settings.github_callback_url,
            "github_authorize_url": self.settings.github_authorize_url,
            "github_token_url": self.settings.github_token_url,
            "github_user_url": self.settings.github_user_url,
            "github_scope": self.settings.github_scope,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing GitHub OAuth settings: {', '.join(missing)}",
            )

    async def _exchange_code_for_token(self, code: str) -> GitHubAccessTokenResponse:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.settings.github_token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.settings.github_client_id,
                    "client_secret": self.settings.github_client_secret,
                    "code": code,
                    "redirect_uri": self.settings.github_callback_url,
                },
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub token exchange failed.",
            )

        payload = response.json()
        if "access_token" not in payload:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub token exchange response was invalid.",
            )
        return GitHubAccessTokenResponse.model_validate(payload)

    async def _fetch_github_user(self, access_token: str) -> GitHubUserProfile:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.settings.github_user_url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub user profile request failed.",
            )

        return GitHubUserProfile.model_validate(response.json())

    async def _upsert_user(self, session: AsyncSession, github_user: GitHubUserProfile) -> User:
        result = await session.execute(select(User).where(User.github_id == str(github_user.id)))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                github_id=str(github_user.id),
                username=github_user.login,
                email=github_user.email,
                name=github_user.name,
                avatar_url=github_user.avatar_url,
            )
            session.add(user)
        else:
            user.username = github_user.login
            user.email = github_user.email
            user.name = github_user.name
            user.avatar_url = github_user.avatar_url

        await session.commit()
        await session.refresh(user)
        return user
