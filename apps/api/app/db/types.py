from __future__ import annotations

from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[list[float]]):
    """PostgreSQL pgvector column without requiring a driver-specific Python package."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_kw: Any) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, _dialect):
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(str(float(item)) for item in value) + "]"
        return process

    def result_processor(self, _dialect, _coltype):
        def process(value: str | list[float] | None) -> list[float] | None:
            if value is None or isinstance(value, list):
                return value
            return [float(item) for item in value.strip("[]").split(",") if item]
        return process
