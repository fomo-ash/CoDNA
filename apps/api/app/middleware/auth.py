from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.modules.auth.utils.jwt import decode_access_token


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.auth = None

        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            if token:
                try:
                    request.state.auth = decode_access_token(request.app.state.settings, token)
                except Exception:
                    request.state.auth = None

        return await call_next(request)
