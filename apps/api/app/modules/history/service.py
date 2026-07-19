from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.repository import Repository
from app.db.models.repository_history_artifact import RepositoryHistoryArtifact
from app.modules.github.client import GitHubClient


class RepositoryHistoryService:
    """Ingest bounded, owner-authorized GitHub decision artifacts."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    async def refresh(
        self, session: AsyncSession, repository_id: UUID, full_name: str, access_token: str | None
    ) -> int:
        artifacts: list[RepositoryHistoryArtifact] = []
        for artifact_type in ("commit", "pull_request", "issue"):
            payload = await self.client.list_repository_history(
                access_token, full_name=full_name, artifact_type=artifact_type
            )
            artifacts.extend(self._to_artifacts(repository_id, artifact_type, payload))
        await session.execute(
            delete(RepositoryHistoryArtifact).where(RepositoryHistoryArtifact.repository_id == repository_id)
        )
        session.add_all(artifacts)
        return len(artifacts)

    async def list(
        self, session: AsyncSession, repository_id: UUID, owner_id: UUID, limit: int
    ) -> list[RepositoryHistoryArtifact]:
        owned = await session.scalar(
            select(Repository.id).where(Repository.id == repository_id, Repository.owner_id == owner_id)
        )
        if owned is None:
            return []
        rows = await session.scalars(
            select(RepositoryHistoryArtifact)
            .where(RepositoryHistoryArtifact.repository_id == repository_id)
            .order_by(RepositoryHistoryArtifact.authored_at.desc().nullslast())
            .limit(limit)
        )
        return rows.all()

    @staticmethod
    def _to_artifacts(
        repository_id: UUID, artifact_type: str, payload: list[dict[str, Any]]
    ) -> list[RepositoryHistoryArtifact]:
        artifacts = []
        for item in payload:
            if artifact_type == "issue" and item.get("pull_request"):
                continue
            if artifact_type == "commit":
                commit = item.get("commit") or {}
                external_id = item.get("sha")
                title = (commit.get("message") or "").split("\n", 1)[0] or None
                body = commit.get("message") or None
                authored_at = RepositoryHistoryService._timestamp((commit.get("author") or {}).get("date"))
            else:
                external_id = str(item.get("number")) if item.get("number") is not None else None
                title = item.get("title")
                body = item.get("body")
                authored_at = RepositoryHistoryService._timestamp(item.get("created_at"))
            url = item.get("html_url")
            if not external_id or not url:
                continue
            author = item.get("author") or {}
            artifacts.append(RepositoryHistoryArtifact(
                repository_id=repository_id,
                provider="github",
                artifact_type=artifact_type,
                external_id=external_id,
                title=title,
                body=body,
                url=url,
                author_login=author.get("login"),
                data={"state": item.get("state"), "labels": [label.get("name") for label in item.get("labels", []) if isinstance(label, dict)]},
                authored_at=authored_at,
            ))
        return artifacts

    @staticmethod
    def _timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
