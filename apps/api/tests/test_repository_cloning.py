from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

import pytest

from app.modules.repositories.clone import (
    RepositoryCloneError,
    RepositoryCloneService,
    RepositoryCloneTarget,
)


REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000101")


def test_clone_repository_builds_safe_clone_command_and_uses_token_environment(tmp_path: Path) -> None:
    recorded: dict[str, object] = {}

    async def fake_runner(command: list[str], cwd: Path, env: dict[str, str]):
        recorded["command"] = command
        recorded["cwd"] = cwd
        recorded["env"] = env
        Path(command[-1]).mkdir(parents=True)
        return 0, "", ""

    service = RepositoryCloneService(str(tmp_path), command_runner=fake_runner)

    result = asyncio.run(
        service.clone_repository(
            RepositoryCloneTarget(
                repository_id=REPOSITORY_ID,
                clone_url="https://github.com/example/repo.git",
                default_branch="main",
                github_access_token="github-token",
            )
        )
    )

    command = recorded["command"]
    env = recorded["env"]

    assert result.clone_path == tmp_path / str(REPOSITORY_ID)
    assert recorded["cwd"] == tmp_path
    assert command == [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        "main",
        "--single-branch",
        "https://github.com/example/repo.git",
        str(tmp_path / str(REPOSITORY_ID)),
    ]
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_VALUE_0"] == "Authorization: Bearer github-token"
    assert "github-token" not in " ".join(command)


def test_clone_repository_removes_partial_clone_on_failure(tmp_path: Path) -> None:
    async def fake_runner(command: list[str], _cwd: Path, _env: dict[str, str]):
        Path(command[-1]).mkdir(parents=True)
        return 1, "", "fatal: repository not found"

    service = RepositoryCloneService(str(tmp_path), command_runner=fake_runner)

    with pytest.raises(RepositoryCloneError, match="repository not found"):
        asyncio.run(
            service.clone_repository(
                RepositoryCloneTarget(
                    repository_id=REPOSITORY_ID,
                    clone_url="https://github.com/example/missing.git",
                    default_branch=None,
                )
            )
        )

    assert not (tmp_path / str(REPOSITORY_ID)).exists()


def test_clone_repository_requires_clone_url(tmp_path: Path) -> None:
    service = RepositoryCloneService(str(tmp_path))

    with pytest.raises(RepositoryCloneError, match="clone URL is missing"):
        asyncio.run(
            service.clone_repository(
                RepositoryCloneTarget(
                    repository_id=REPOSITORY_ID,
                    clone_url=None,
                    default_branch="main",
                )
            )
        )
