from __future__ import annotations

from pydantic import BaseModel


class GitHubAccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    scope: str | None = None


class GitHubProfileResponse(BaseModel):
    id: int
    login: str
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None


class GitHubProfile(BaseModel):
    github_id: str
    username: str
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None


class GitHubRepository(BaseModel):
    github_id: str
    name: str
    full_name: str
    default_branch: str | None = None
    clone_url: str
    visibility: str
    private: bool


class GitHubRepositoryListResponse(BaseModel):
    repositories: list[GitHubRepository]
    page: int
    per_page: int
    has_next_page: bool

