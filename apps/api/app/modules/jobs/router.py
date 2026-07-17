from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db_session
from app.db.models.user import User
from app.modules.auth.dependencies import get_current_user_record
from app.modules.jobs.dependencies import get_job_service
from app.modules.jobs.interfaces import JobService
from app.modules.jobs.schemas import JobRead
from app.modules.jobs.service import JobNotFoundError


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead, status_code=status.HTTP_200_OK)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user_record),
    session: AsyncSession = Depends(get_db_session),
    service: JobService = Depends(get_job_service),
) -> JobRead:
    try:
        return await service.get_job(session, job_id, current_user.id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        ) from exc
