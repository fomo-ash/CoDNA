from __future__ import annotations

from app.core.config import get_settings
from app.modules.questions.service import RepositoryQuestionService
from app.modules.retrieval.dependencies import get_repository_retrieval_service


def get_repository_question_service() -> RepositoryQuestionService:
    return RepositoryQuestionService(get_settings(), get_repository_retrieval_service())
