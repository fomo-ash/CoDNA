from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.repository_answer_usage import RepositoryAnswerUsage


class AnswerBudgetExceededError(RuntimeError):
    pass


class AnswerUsageTracker(Protocol):
    async def reserve(
        self, session: AsyncSession, owner_id: UUID, repository_id: UUID, provider: str, model: str, maximum_cost: Decimal
    ) -> object: ...

    async def finalize(
        self, session: AsyncSession, reservation: object, input_tokens: int, output_tokens: int,
        actual_cost: Decimal, status: str,
    ) -> None: ...


class DatabaseAnswerUsageTracker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def reserve(
        self, session: AsyncSession, owner_id: UUID, repository_id: UUID, provider: str, model: str, maximum_cost: Decimal
    ) -> RepositoryAnswerUsage:
        spent = await session.scalar(
            select(func.coalesce(func.sum(RepositoryAnswerUsage.cost_usd), 0)).where(
                RepositoryAnswerUsage.status.in_(("reserved", "completed")),
            )
        )
        if Decimal(str(spent)) + maximum_cost > self.settings.answer_budget_usd:
            raise AnswerBudgetExceededError(
                f"Total project answer budget of ${self.settings.answer_budget_usd:.2f} has been reached."
            )
        reservation = RepositoryAnswerUsage(
            owner_id=owner_id,
            repository_id=repository_id,
            provider=provider,
            model=model,
            cost_usd=maximum_cost,
            status="reserved",
        )
        session.add(reservation)
        await session.commit()
        await session.refresh(reservation)
        return reservation

    async def finalize(
        self, session: AsyncSession, reservation: RepositoryAnswerUsage, input_tokens: int, output_tokens: int,
        actual_cost: Decimal, status: str,
    ) -> None:
        reservation.input_tokens = input_tokens
        reservation.output_tokens = output_tokens
        reservation.cost_usd = actual_cost
        reservation.status = status
        await session.commit()
