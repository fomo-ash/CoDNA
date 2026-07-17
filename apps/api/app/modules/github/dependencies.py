from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.modules.github.service import GitHubServiceImpl


def get_github_service(request: Request) -> GitHubServiceImpl:
    settings: Settings = request.app.state.settings
    return GitHubServiceImpl(settings=settings)
