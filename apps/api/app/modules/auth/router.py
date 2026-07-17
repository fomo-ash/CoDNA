from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.modules.auth.dependencies import get_auth_service, get_current_user
from app.modules.auth.interfaces import AuthService
from app.modules.auth.schemas import AuthCallbackQuery, AuthLoginResponse, AuthTokenResponse, CurrentUser


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login", response_model=AuthLoginResponse, status_code=status.HTTP_200_OK)
async def github_login(
    service: AuthService = Depends(get_auth_service),
) -> AuthLoginResponse:
    try:
        authorization_url = await service.get_github_login_url()
        return AuthLoginResponse(authorization_url=authorization_url)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc


@router.get("/github/callback", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> AuthTokenResponse:
    payload = AuthCallbackQuery(code=code, state=state)
    return await service.authenticate_with_github(session, payload)


@router.get("/me", response_model=CurrentUser, status_code=status.HTTP_200_OK)
async def read_current_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user
