from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthLoginResponse(BaseModel):
    authorization_url: str


class AuthCallbackQuery(BaseModel):
    code: str
    state: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "CurrentUser"


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    github_id: str
    username: str
    email: str | None
    name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime

