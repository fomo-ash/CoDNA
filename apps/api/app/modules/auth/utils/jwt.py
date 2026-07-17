from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import Settings


def create_access_token(
    settings: Settings,
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    if not settings.jwt_expire_minutes:
        raise RuntimeError("JWT settings are not configured.")
    token = _create_signed_token(
        settings=settings,
        subject=subject,
        expires_minutes=settings.jwt_expire_minutes,
        extra_claims=extra_claims,
    )
    return token, settings.jwt_expire_minutes * 60


def create_oauth_state_token(settings: Settings) -> str:
    if not settings.oauth_state_expire_minutes:
        raise RuntimeError("JWT settings are not configured.")
    return _create_signed_token(
        settings=settings,
        subject="github-oauth",
        expires_minutes=settings.oauth_state_expire_minutes,
        extra_claims={"kind": "oauth_state"},
    )


def decode_oauth_state_token(settings: Settings, token: str) -> dict[str, Any]:
    payload = decode_access_token(settings, token)
    if payload.get("kind") != "oauth_state":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OAuth state.")
    return payload


def _create_signed_token(
    settings: Settings,
    subject: str,
    expires_minutes: int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    if not settings.jwt_secret or not settings.jwt_algorithm:
        raise RuntimeError("JWT settings are not configured.")

    expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires_at,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    if not settings.jwt_secret or not settings.jwt_algorithm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT settings are not configured.",
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")
    return payload
