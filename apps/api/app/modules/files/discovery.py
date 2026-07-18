from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path


DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".github",
        ".hg",
        ".idea",
        ".svn",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "vendor",
        "venv",
        ".next",
    }
)

IGNORED_FILE_NAMES = frozenset(
    {
        ".DS_Store",
        ".env",
        ".env.development",
        ".env.local",
        ".env.production",
        ".env.test",
        ".npmrc",
        ".pypirc",
        "id_rsa",
        "id_rsa.pub",
    }
)

IGNORED_BINARY_EXTENSIONS = frozenset(
    {
        "dll",
        "exe",
        "gif",
        "gz",
        "ico",
        "jar",
        "jpeg",
        "jpg",
        "pdf",
        "png",
        "tar",
        "zip",
    }
)

LANGUAGE_BY_EXTENSION = {
    "c": "C",
    "cc": "C++",
    "cpp": "C++",
    "cs": "C#",
    "css": "CSS",
    "go": "Go",
    "h": "C",
    "hpp": "C++",
    "html": "HTML",
    "java": "Java",
    "js": "JavaScript",
    "json": "JSON",
    "jsx": "JavaScript",
    "kt": "Kotlin",
    "md": "Markdown",
    "php": "PHP",
    "py": "Python",
    "rb": "Ruby",
    "rs": "Rust",
    "sh": "Shell",
    "sql": "SQL",
    "swift": "Swift",
    "toml": "TOML",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "xml": "XML",
    "yaml": "YAML",
    "yml": "YAML",
}

LANGUAGE_BY_FILENAME = {
    "Dockerfile": "Dockerfile",
    "Makefile": "Makefile",
}


class RepositoryFileDiscoveryError(Exception):
    pass


@dataclass(frozen=True)
class DiscoveredRepositoryFile:
    path: str
    filename: str
    extension: str | None
    language: str | None
    size_bytes: int
    sha256: str
    is_binary: bool
    discovered_at: datetime


@dataclass(frozen=True)
class RepositoryInventoryStats:
    total_files: int
    source_files: int
    binary_files: int
    total_size_bytes: int
    detected_languages: dict[str, int]
    last_scan_at: datetime


@dataclass(frozen=True)
class RepositoryDiscoveryResult:
    files: list[DiscoveredRepositoryFile]
    stats: RepositoryInventoryStats


class RepositoryFileDiscoveryService:
    def __init__(
        self,
        *,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_files: int | None = None,
    ) -> None:
        if max_file_size_bytes <= 0:
            raise RepositoryFileDiscoveryError("Maximum file size must be greater than zero.")
        if max_files is not None and max_files <= 0:
            raise RepositoryFileDiscoveryError("Maximum file count must be greater than zero.")
        self.max_file_size_bytes = max_file_size_bytes
        self.max_files = max_files

    def discover(self, repository_path: Path) -> RepositoryDiscoveryResult:
        root = Path(repository_path).resolve()
        if not root.is_dir():
            raise RepositoryFileDiscoveryError("Repository clone path does not exist.")

        discovered_at = datetime.now(UTC)
        files: list[DiscoveredRepositoryFile] = []
        languages: dict[str, int] = {}
        binary_files = 0
        total_size_bytes = 0

        for file_path in self._iter_candidate_files(root):
            if self.max_files is not None and len(files) >= self.max_files:
                break

            try:
                file_stat = file_path.stat()
            except OSError:
                continue

            if file_stat.st_size > self.max_file_size_bytes:
                continue

            extension = file_path.suffix.lower().removeprefix(".") or None
            if extension in IGNORED_BINARY_EXTENSIONS:
                continue

            try:
                file_hash, is_binary = self._hash_and_detect_binary(file_path)
            except OSError:
                continue
            language = None if is_binary else self._detect_language(file_path, extension)
            relative_path = file_path.relative_to(root).as_posix()

            files.append(
                DiscoveredRepositoryFile(
                    path=relative_path,
                    filename=file_path.name,
                    extension=extension,
                    language=language,
                    size_bytes=file_stat.st_size,
                    sha256=file_hash,
                    is_binary=is_binary,
                    discovered_at=discovered_at,
                )
            )
            total_size_bytes += file_stat.st_size
            if is_binary:
                binary_files += 1
            elif language is not None:
                languages[language] = languages.get(language, 0) + 1

        stats = RepositoryInventoryStats(
            total_files=len(files),
            source_files=sum(1 for file in files if not file.is_binary and file.language is not None),
            binary_files=binary_files,
            total_size_bytes=total_size_bytes,
            detected_languages=dict(sorted(languages.items())),
            last_scan_at=discovered_at,
        )
        return RepositoryDiscoveryResult(files=files, stats=stats)

    def _iter_candidate_files(self, root: Path):
        for directory_path, directory_names, file_names in os.walk(root):
            directory_names[:] = sorted(
                name for name in directory_names if name not in IGNORED_DIRECTORY_NAMES
            )

            current_directory = Path(directory_path)
            for file_name in sorted(file_names):
                if file_name in IGNORED_FILE_NAMES:
                    continue

                file_path = current_directory / file_name
                if file_path.is_symlink() or not file_path.is_file():
                    continue

                yield file_path

    def _detect_language(self, file_path: Path, extension: str | None) -> str | None:
        return LANGUAGE_BY_FILENAME.get(file_path.name) or LANGUAGE_BY_EXTENSION.get(extension or "")

    def _hash_and_detect_binary(self, file_path: Path) -> tuple[str, bool]:
        digest = sha256()
        has_null_byte = False

        with file_path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)
                if b"\0" in chunk:
                    has_null_byte = True

        return digest.hexdigest(), has_null_byte

    def discover_files(self, repository_path: Path) -> list[DiscoveredRepositoryFile]:
        return self.discover(repository_path).files
