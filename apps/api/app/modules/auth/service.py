from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.user import User
from app.modules.auth.schemas import (
    AuthCallbackQuery,
    AuthTokenResponse,
    CurrentUser,
)
from app.modules.github.service import GitHubAuthorizationRequiredError, GitHubIntegrationError, GitHubServiceImpl
from app.modules.github.schemas import GitHubProfile
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

        github_service = GitHubServiceImpl(self.settings)
        try:
            token_response = await github_service.exchange_code(payload.code)
            github_user = await github_service.get_profile_for_token(token_response.access_token)
        except (GitHubAuthorizationRequiredError, GitHubIntegrationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub authentication failed.",
            ) from exc
        user = await self._upsert_user(session, github_user, token_response.access_token)

        access_token, expires_in = create_access_token(self.settings, str(user.id))
        return AuthTokenResponse(
            access_token=access_token,
            expires_in=expires_in,
            user=CurrentUser.model_validate(user),
        )

    async def get_current_user(self, session: AsyncSession, user_id: str) -> CurrentUser:
        user = await self.get_current_user_record(session, user_id)
        return CurrentUser.model_validate(user)

    async def get_current_user_record(self, session: AsyncSession, user_id: str) -> User:
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
        return user

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

    async def _upsert_user(
        self,
        session: AsyncSession,
        github_user: GitHubProfile,
        access_token: str,
    ) -> User:
        result = await session.execute(select(User).where(User.github_id == github_user.github_id))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                github_id=github_user.github_id,
                username=github_user.username,
                email=github_user.email,
                name=github_user.name,
                avatar_url=github_user.avatar_url,
                github_access_token=access_token,
            )
            session.add(user)
        else:
            user.username = github_user.username
            user.email = github_user.email
            user.name = github_user.name
            user.avatar_url = github_user.avatar_url
            user.github_access_token = access_token

        await session.commit()
        await session.refresh(user)
        return user
