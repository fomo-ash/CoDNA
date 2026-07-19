from __future__ import annotations

from app.core.config import get_settings
from app.modules.retrieval.service import RepositoryRetrievalService


def get_repository_retrieval_service() -> RepositoryRetrievalService:
    return RepositoryRetrievalService(get_settings())
