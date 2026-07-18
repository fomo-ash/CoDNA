from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from app.db.models.repository_file import RepositoryFile
from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.service import KnowledgeExtractionContext, KnowledgeItem


CONFIG_FILENAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "tsconfig.json",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}


class ConfigurationKnowledgeExtractor:
    name = "configuration"

    def extract(self, context: KnowledgeExtractionContext) -> list[KnowledgeItem]:
        items: list[KnowledgeItem] = []
        for file in context.files:
            if file.is_binary or not self._is_config_file(file):
                continue

            file_path = context.repository_path / file.path
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            data = self._extract_file_data(file_path, file, text)
            if not data:
                continue

            items.append(
                KnowledgeItem(
                    repository_file_id=file.id,
                    path=file.path,
                    source_type=RepositoryKnowledgeSourceType.CONFIGURATION,
                    item_type=data["item_type"],
                    name=data.get("name") or file.path,
                    extractor=self.name,
                    data=data,
                )
            )
        return items

    def _is_config_file(self, file: RepositoryFile) -> bool:
        name = file.filename
        return name in CONFIG_FILENAMES or name.endswith(".Dockerfile") or name.startswith("Dockerfile.")

    def _extract_file_data(self, file_path: Path, file: RepositoryFile, text: str) -> dict:
        if file.filename == "package.json":
            return self._parse_package_json(text)
        if file.filename == "pyproject.toml":
            return self._parse_pyproject(text)
        if file.filename in {"requirements.txt", "requirements-dev.txt"}:
            return self._parse_requirements(file.filename, text)
        if file.filename == "tsconfig.json":
            return self._parse_tsconfig(text)
        if file.filename == "Dockerfile" or file.filename.endswith(".Dockerfile") or file.filename.startswith("Dockerfile."):
            return self._parse_dockerfile(text)
        if file.filename in {"docker-compose.yml", "docker-compose.yaml"}:
            return self._parse_compose(text)
        return {}

    def _parse_package_json(self, text: str) -> dict:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {"item_type": "package_manifest", "parse_error": "Invalid JSON."}

        dependency_groups = {
            key: data.get(key, {})
            for key in (
                "dependencies",
                "devDependencies",
                "peerDependencies",
                "optionalDependencies",
            )
            if isinstance(data.get(key), dict)
        }
        dependencies = sorted(
            {name for group in dependency_groups.values() for name in group.keys()}
        )
        return {
            "item_type": "package_manifest",
            "name": data.get("name"),
            "package_manager": self._detect_package_manager(data),
            "scripts": data.get("scripts", {}),
            "dependency_groups": dependency_groups,
            "dependencies": dependencies,
            "frameworks": self._detect_frameworks(dependencies),
            "runtime": {
                "node": data.get("engines", {}).get("node") if isinstance(data.get("engines"), dict) else None
            },
        }

    def _parse_pyproject(self, text: str) -> dict:
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return {"item_type": "python_project", "parse_error": "Invalid TOML."}

        project = data.get("project", {})
        poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
        dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
        poetry_dependencies = poetry.get("dependencies", {}) if isinstance(poetry, dict) else {}
        names = list(dependencies)
        if isinstance(poetry_dependencies, dict):
            names.extend(poetry_dependencies.keys())
        return {
            "item_type": "python_project",
            "name": project.get("name") if isinstance(project, dict) else poetry.get("name"),
            "dependencies": names,
            "frameworks": self._detect_frameworks(names),
            "build_system": data.get("build-system", {}),
        }

    def _parse_requirements(self, filename: str, text: str) -> dict:
        dependencies = []
        for line in text.splitlines():
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#") or clean_line.startswith("-"):
                continue
            dependencies.append(re.split(r"[<>=~! ]+", clean_line, maxsplit=1)[0])
        return {
            "item_type": "python_requirements",
            "name": filename,
            "dependencies": dependencies,
            "frameworks": self._detect_frameworks(dependencies),
        }

    def _parse_tsconfig(self, text: str) -> dict:
        try:
            data = json.loads(self._strip_json_comments(text))
        except json.JSONDecodeError:
            return {"item_type": "typescript_config", "parse_error": "Invalid JSON."}
        compiler_options = data.get("compilerOptions", {})
        return {
            "item_type": "typescript_config",
            "extends": data.get("extends"),
            "compiler_options": compiler_options,
            "paths": compiler_options.get("paths", {}) if isinstance(compiler_options, dict) else {},
            "include": data.get("include", []),
            "exclude": data.get("exclude", []),
        }

    def _parse_dockerfile(self, text: str) -> dict:
        instructions = []
        base_images = []
        exposed_ports = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            instruction = stripped.split(maxsplit=1)[0].upper()
            value = stripped[len(instruction) :].strip()
            instructions.append({"instruction": instruction, "value": value, "line": line_number})
            if instruction == "FROM":
                base_images.append(value.split()[0])
            elif instruction == "EXPOSE":
                exposed_ports.extend(value.split())
        return {
            "item_type": "dockerfile",
            "base_images": base_images,
            "exposed_ports": exposed_ports,
            "instructions": instructions,
            "runtime": self._detect_runtime_from_images(base_images),
        }

    def _parse_compose(self, text: str) -> dict:
        services = []
        current_service = None
        in_services = False
        for raw_line in text.splitlines():
            if raw_line.strip() == "services:":
                in_services = True
                continue
            if not in_services:
                continue
            match = re.match(r"^\s{2}([A-Za-z0-9_.-]+):\s*$", raw_line)
            if match:
                current_service = {"name": match.group(1), "image": None, "build": None, "ports": []}
                services.append(current_service)
                continue
            if current_service is None:
                continue
            image_match = re.match(r"^\s{4}image:\s*(.+)\s*$", raw_line)
            build_match = re.match(r"^\s{4}build:\s*(.+)\s*$", raw_line)
            port_match = re.match(r'^\s{6}-\s*"?([^"]+)"?\s*$', raw_line)
            if image_match:
                current_service["image"] = image_match.group(1)
            elif build_match:
                current_service["build"] = build_match.group(1)
            elif port_match:
                current_service["ports"].append(port_match.group(1))
        return {
            "item_type": "compose_config",
            "services": services,
            "service_count": len(services),
        }

    def _strip_json_comments(self, text: str) -> str:
        text = re.sub(r"//.*", "", text)
        return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    def _detect_package_manager(self, data: dict) -> str | None:
        package_manager = data.get("packageManager")
        if isinstance(package_manager, str):
            return package_manager.split("@", 1)[0]
        return None

    def _detect_frameworks(self, dependencies: list[str]) -> list[str]:
        dependency_names = {dependency.lower() for dependency in dependencies}
        frameworks = []
        checks = {
            "next": "Next.js",
            "react": "React",
            "vue": "Vue",
            "vite": "Vite",
            "express": "Express",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "prisma": "Prisma",
            "tailwindcss": "Tailwind CSS",
        }
        for dependency, framework in checks.items():
            if dependency in dependency_names or f"@{dependency}" in dependency_names:
                frameworks.append(framework)
        return frameworks

    def _detect_runtime_from_images(self, base_images: list[str]) -> list[str]:
        runtimes = []
        for image in base_images:
            lower_image = image.lower()
            if "python" in lower_image:
                runtimes.append("Python")
            if "node" in lower_image:
                runtimes.append("Node.js")
            if "postgres" in lower_image:
                runtimes.append("PostgreSQL")
            if "redis" in lower_image:
                runtimes.append("Redis")
        return sorted(set(runtimes))
