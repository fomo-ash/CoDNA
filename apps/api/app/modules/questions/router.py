from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.embeddings.service import EmbeddingConfigurationError
from app.modules.questions.dependencies import get_repository_question_service
from app.modules.questions.budget import AnswerBudgetExceededError
from app.modules.questions.schemas import (
    RepositoryImpactExplanationRequest,
    RepositoryQuestionRequest,
    RepositoryQuestionResponse,
)
from app.modules.questions.service import AnswerProviderError, RepositoryQuestionService
from app.modules.repositories.service import RepositoryNotFoundError


router = APIRouter(prefix="/repositories", tags=["repository-questions"])


async def check_and_increment_rate_limit(request: Request, repository_id: UUID, user_id: UUID) -> None:
    settings = get_settings()
    if not settings.question_rate_limit_per_repo or settings.question_rate_limit_per_repo <= 0:
        return

    redis_client = getattr(request.app.state, "redis", None)
    if not redis_client:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:question:{repository_id}:{user_id}:{client_ip}"

    count_str = await redis_client.get(key)
    if count_str and int(count_str) >= settings.question_rate_limit_per_repo:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Demo question limit reached (1 question per repository). "
                "For the full experience of asking unlimited questions, please check out SETUP.md and add your API key, "
                "or contact me via email (ashutoshbadapanda02@gmail.com)."
            ),
        )
    await redis_client.incr(key)
    await redis_client.expire(key, 86400)


@router.post("/{repository_id}/impact/explain", response_model=RepositoryQuestionResponse)
async def explain_repository_impact(
    repository_id: UUID,
    payload: RepositoryImpactExplanationRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryQuestionService = Depends(get_repository_question_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryQuestionResponse:
    await check_and_increment_rate_limit(request, repository_id, current_user.id)
    question = payload.question or (
        f"Analyze the change impact of {payload.path} using the authoritative traversal."
    )
    try:
        return await service.ask(
            session, repository_id, current_user.id, question, payload.path, payload.depth
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc
    except EmbeddingConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AnswerBudgetExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except AnswerProviderError as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Answer provider request failed.") from exc


@router.post("/{repository_id}/questions", response_model=RepositoryQuestionResponse)
async def ask_repository_question(
    repository_id: UUID,
    payload: RepositoryQuestionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryQuestionService = Depends(get_repository_question_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryQuestionResponse:
    await check_and_increment_rate_limit(request, repository_id, current_user.id)
    try:
        return await service.ask(
            session, repository_id, current_user.id, payload.question, payload.impact_path, payload.impact_depth
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.") from exc
    except EmbeddingConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AnswerBudgetExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except AnswerProviderError as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Answer provider request failed.") from exc

