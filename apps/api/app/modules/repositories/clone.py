from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID


GitCommandRunner = Callable[[list[str], Path, dict[str, str]], Awaitable[tuple[int, str, str]]]


class RepositoryCloneError(Exception):
    pass


@dataclass(frozen=True)
class RepositoryCloneTarget:
    repository_id: UUID
    clone_url: str | None
    default_branch: str | None
    github_access_token: str | None = None


@dataclass(frozen=True)
class RepositoryCloneResult:
    clone_path: Path
    cloned_at: datetime


class RepositoryCloneService:
    def __init__(
        self,
        workspace_path: str,
        command_runner: GitCommandRunner | None = None,
    ) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.command_runner = command_runner or self._run_git_command

    def get_clone_path(self, repository_id: UUID) -> Path:
        return self.workspace_path / str(repository_id)

    async def clone_repository(self, target: RepositoryCloneTarget) -> RepositoryCloneResult:
        if not target.clone_url:
            raise RepositoryCloneError("Repository clone URL is missing.")

        clone_path = self.get_clone_path(target.repository_id)
        self._ensure_safe_clone_path(clone_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)

        if clone_path.exists():
            shutil.rmtree(clone_path)

        command = self._build_clone_command(target.clone_url, target.default_branch, clone_path)
        env = self._build_git_environment(target.clone_url, target.github_access_token)
        return_code, _stdout, stderr = await self.command_runner(command, self.workspace_path, env)

        if return_code != 0:
            if clone_path.exists():
                shutil.rmtree(clone_path)
            raise RepositoryCloneError(self._format_git_error(stderr))

        return RepositoryCloneResult(clone_path=clone_path, cloned_at=datetime.now(UTC))

    def _ensure_safe_clone_path(self, clone_path: Path) -> None:
        resolved_workspace = self.workspace_path.resolve()
        resolved_clone_path = clone_path.resolve()
        if not resolved_clone_path.is_relative_to(resolved_workspace):
            raise RepositoryCloneError("Repository clone path is outside the configured workspace.")

    def _build_clone_command(
        self,
        clone_url: str,
        default_branch: str | None,
        clone_path: Path,
    ) -> list[str]:
        command = ["git", "clone", "--depth", "1"]
        if default_branch:
            command.extend(["--branch", default_branch, "--single-branch"])
        command.extend([clone_url, str(clone_path)])
        return command

    def _build_git_environment(
        self,
        clone_url: str,
        github_access_token: str | None,
    ) -> dict[str, str]:
        environment = {"GIT_TERMINAL_PROMPT": "0"}
        if github_access_token:
            parsed_clone_url = urlparse(clone_url)
            if not parsed_clone_url.scheme or not parsed_clone_url.netloc:
                raise RepositoryCloneError("Repository clone URL is invalid.")
            environment.update(
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": (
                        f"http.{parsed_clone_url.scheme}://{parsed_clone_url.netloc}/.extraheader"
                    ),
                    "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {github_access_token}",
                }
            )
        return environment

    def _format_git_error(self, stderr: str) -> str:
        if not stderr:
            return "Repository clone failed."
        return stderr.strip()[:1000]

    async def _run_git_command(
        self,
        command: list[str],
        cwd: Path,
        env: dict[str, str],
    ) -> tuple[int, str, str]:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            process.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
