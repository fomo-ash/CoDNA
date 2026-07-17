from __future__ import annotations

from fastapi import APIRouter, Request

from app.db.session import check_database_connection


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    db_status = "ok"
    redis_status = "ok"
    details: dict[str, str] = {}

    try:
        await check_database_connection(request.app.state.db_engine)
    except Exception as exc:  # pragma: no cover - defensive readiness path
        db_status = "error"
        details["database"] = str(exc)

    try:
        await request.app.state.redis.ping()
    except Exception as exc:  # pragma: no cover - defensive readiness path
        redis_status = "error"
        details["redis"] = str(exc)

    status = "ready" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": status,
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        },
        "details": details,
    }
