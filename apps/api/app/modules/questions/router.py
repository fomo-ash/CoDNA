from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/{repository_id}/impact/explain", response_model=RepositoryQuestionResponse)
async def explain_repository_impact(
    repository_id: UUID,
    payload: RepositoryImpactExplanationRequest,
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryQuestionService = Depends(get_repository_question_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryQuestionResponse:
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
    session: AsyncSession = Depends(get_db_session),
    service: RepositoryQuestionService = Depends(get_repository_question_service),
    current_user: User = Depends(get_current_user_record),
) -> RepositoryQuestionResponse:
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
