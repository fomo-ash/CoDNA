from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schemas import AuthCallbackQuery, AuthTokenResponse, CurrentUser


class AuthService(Protocol):
    async def get_github_login_url(self) -> str:
        ...

    async def authenticate_with_github(
        self,
        session: AsyncSession,
        payload: AuthCallbackQuery,
    ) -> AuthTokenResponse:
        ...

    async def get_current_user(self, session: AsyncSession, user_id: str) -> CurrentUser:
        ...
