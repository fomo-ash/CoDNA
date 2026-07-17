from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.dependencies import get_db_session
from app.modules.auth.interfaces import AuthService
from app.modules.auth.service import AuthServiceImpl
from app.modules.auth.utils.jwt import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(request: Request) -> AuthService:
    settings: Settings = request.app.state.settings
    return AuthServiceImpl(settings=settings)


async def get_authenticated_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    payload = decode_access_token(request.app.state.settings, credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")
    return str(subject)


async def get_current_user(
    user_id: str = Depends(get_authenticated_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return await service.get_current_user(session, user_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
