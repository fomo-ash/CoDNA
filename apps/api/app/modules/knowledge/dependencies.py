from __future__ import annotations

from app.modules.knowledge.interfaces import RepositoryKnowledgeService
from app.modules.knowledge.service import RepositoryKnowledgeServiceImpl


def get_repository_knowledge_service() -> RepositoryKnowledgeService:
    return RepositoryKnowledgeServiceImpl()
