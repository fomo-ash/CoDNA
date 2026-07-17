from __future__ import annotations

from enum import Enum


class RepositoryStatus(str, Enum):
    REGISTERED = "registered"
    CLONING = "cloning"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"
