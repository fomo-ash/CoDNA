from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.db.session import create_engine, create_session_factory
from app.middleware.auth import AuthContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = app.state.settings
    logger = logging.getLogger("app.lifecycle")
    logger.info("application starting")
    logger.info("environment=%s", app_settings.app_env)

    app.state.db_engine = create_engine(app_settings)
    app.state.session_factory = create_session_factory(app.state.db_engine)
    app.state.redis = Redis.from_url(
        app_settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("Redis initialized")

    if getattr(app_settings, "otel_enabled", True):
        setup_telemetry(app=app, db_engine=app.state.db_engine)

    try:
        logger.info("application ready")
        yield
    finally:
        await app.state.redis.aclose()
        await app.state.db_engine.dispose()


def create_app() -> FastAPI:
    app_settings = get_settings()
    setup_logging(app_settings.log_level)

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    allowed_origins = [app_settings.frontend_url, "http://localhost:3333", "http://localhost:3000"]
    allowed_origins = [o.rstrip('/') for o in allowed_origins if o]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthContextMiddleware)
    app.state.settings = app_settings

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": app_settings.app_name,
            "version": app_settings.app_version,
            "status": "running",
            "docs": app.docs_url or "/docs",
        }

    app.include_router(api_router)
    return app


app = create_app()
