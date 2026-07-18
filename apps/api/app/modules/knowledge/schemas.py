from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryKnowledgeItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID | None
    path: str | None
    source_type: str
    item_type: str
    name: str | None
    extractor: str
    data: dict
    extracted_at: datetime
    created_at: datetime
    updated_at: datetime


class RepositoryKnowledgeItemListResponse(BaseModel):
    knowledge_items: list[RepositoryKnowledgeItemRead]
    page: int
    page_size: int
    has_next_page: bool
