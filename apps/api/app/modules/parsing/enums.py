from __future__ import annotations

from enum import StrEnum


class RepositoryFileParseStatus(StrEnum):
    PARSED = "parsed"
    SYNTAX_ERROR = "syntax_error"
    UNSUPPORTED = "unsupported"
    SKIPPED = "skipped"
    FAILED = "failed"
