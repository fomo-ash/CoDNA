from __future__ import annotations

from enum import StrEnum


class RepositoryKnowledgeSourceType(StrEnum):
    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    DATABASE_SCHEMA = "database_schema"
    CONFIGURATION = "configuration"
