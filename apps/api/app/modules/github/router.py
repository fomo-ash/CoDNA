from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.github.dependencies import get_github_service
from app.modules.github.schemas import GitHubProfile, GitHubRepositoryListResponse
from app.modules.github.service import (
    GitHubAuthorizationRequiredError,
    GitHubIntegrationError,
    GitHubServiceImpl,
)


router = APIRouter(prefix="/github", tags=["github"])


@router.get("/me", response_model=GitHubProfile, status_code=status.HTTP_200_OK)
async def get_github_profile(
    current_user: User = Depends(get_current_user_record),
    service: GitHubServiceImpl = Depends(get_github_service),
) -> GitHubProfile:
    try:
        return await service.get_profile(current_user)
    except GitHubAuthorizationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub authorization is required.",
        ) from exc
    except GitHubIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub profile request failed.",
        ) from exc


@router.get("/repositories", response_model=GitHubRepositoryListResponse, status_code=status.HTTP_200_OK)
async def list_github_repositories(
    visibility: Literal["all", "public", "private"] = Query("all"),
    sort: Literal["created", "updated", "pushed", "full_name"] = Query("updated"),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user_record),
    service: GitHubServiceImpl = Depends(get_github_service),
) -> GitHubRepositoryListResponse:
    try:
        return await service.list_repositories(
            current_user,
            visibility=visibility,
            sort=sort,
            page=page,
            per_page=per_page,
        )
    except GitHubAuthorizationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub authorization is required.",
        ) from exc
    except GitHubIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub repository listing failed.",
        ) from exc
