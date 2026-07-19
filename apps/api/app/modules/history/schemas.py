from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryHistoryArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    provider: str
    artifact_type: str
    external_id: str
    title: str | None
    body: str | None
    url: str
    author_login: str | None
    path: str | None
    data: dict
    authored_at: datetime | None


class RepositoryHistoryListResponse(BaseModel):
    repository_id: UUID
    artifacts: list[RepositoryHistoryArtifactRead]
