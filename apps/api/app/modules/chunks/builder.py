from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable
import re
import posixpath
from uuid import UUID

from app.db.models.repository_knowledge_item import RepositoryKnowledgeItem
from app.modules.chunks.models import SemanticChunk


SMALL_SOURCE_FILE_MAX_LINES = 40


class SemanticChunkBuilder:
    """Build semantic documents from persisted knowledge; it never invokes parsers."""

    def __init__(self) -> None:
        self._repository_id: str | None = None

    def build(
        self,
        repository_path: Path,
        knowledge_items: Iterable[RepositoryKnowledgeItem],
        repository_id: UUID | None = None,
    ) -> list[SemanticChunk]:
        self._repository_id = str(repository_id) if repository_id else None
        items_by_path: dict[str, list[RepositoryKnowledgeItem]] = defaultdict(list)
        for item in knowledge_items:
            if item.path:
                items_by_path[item.path].append(item)

        chunks: list[SemanticChunk] = []
        for path, items in items_by_path.items():
            content = self._read_file(repository_path, path)
            if content is None:
                continue
            source_type = items[0].source_type
            if source_type == "source_code":
                chunks.extend(self._build_source_chunks(path, content, items))
            elif source_type == "documentation":
                chunks.extend(self._build_documentation_chunks(path, content, items))
            elif source_type == "database_schema":
                chunks.extend(self._build_prisma_chunks(path, content, items))
            elif source_type == "configuration":
                chunks.extend(self._build_configuration_chunks(path, content, items))
        self._resolve_relationships(chunks)
        return chunks

    def _build_source_chunks(
        self,
        path: str,
        content: str,
        items: list[RepositoryKnowledgeItem],
    ) -> list[SemanticChunk]:
        source_file = next((item for item in items if item.item_type == "source_file"), None)
        if source_file is None:
            return []
        language = source_file.data.get("language")
        parser = source_file.data.get("parser")
        imports = [item.data for item in items if item.item_type == "import"]
        symbols = [item.data for item in items if item.item_type == "symbol"]
        classes = [symbol for symbol in symbols if symbol.get("kind") == "class"]
        functions = [
            symbol
            for symbol in symbols
            if symbol.get("kind") in {"function", "method"} and not symbol.get("parent_symbol")
        ]
        chunks = [
            self._source_class_chunk(path, content, source_file.repository_file_id, language, parser, imports, symbols, symbol)
            for symbol in classes
        ]
        chunks.extend(
            self._source_function_chunk(path, content, source_file.repository_file_id, language, parser, imports, symbol)
            for symbol in functions
        )
        chunks.extend(
            self._source_symbol_group_chunks(
                path, content, source_file.repository_file_id, language, parser, imports, symbols
            )
        )
        if not chunks and len(content.splitlines()) <= SMALL_SOURCE_FILE_MAX_LINES:
            chunk_type = self._specialized_source_file_type(path, content, symbols)
            chunks.append(
                SemanticChunk(
                    repository_file_id=source_file.repository_file_id,
                    path=path,
                    chunk_type=chunk_type,
                    source_type="source_code",
                    title=path,
                    language=language,
                    content=content,
                    start_line=1,
                    end_line=max(1, len(content.splitlines())),
                    metadata={
                        **self._repository_metadata(path, language, 1, max(1, len(content.splitlines())), parser),
                        "imports": imports,
                        "file_imports": imports,
                        "symbols": symbols,
                        "exports": source_file.data.get("exports", []),
                    },
                )
            )
        return chunks

    def _source_class_chunk(
        self, path, content, repository_file_id, language, parser, imports, symbols, symbol
    ) -> SemanticChunk:
        name = symbol["name"]
        methods = [
            candidate
            for candidate in symbols
            if candidate.get("parent_symbol") == name and candidate.get("kind") in {"function", "method"}
        ]
        class_calls = self._unique_values(
            value for method in methods for value in method.get("calls", [])
        )
        class_references = self._unique_values(
            value for method in methods for value in method.get("references", [])
        )
        class_usage = class_calls + class_references
        return SemanticChunk(
            repository_file_id=repository_file_id,
            path=path,
            chunk_type="class",
            source_type="source_code",
            title=name,
            language=language,
            content=self._slice_lines(content, symbol.get("start_line"), symbol.get("end_line")),
            start_line=symbol.get("start_line"),
            end_line=symbol.get("end_line"),
            metadata={
                **self._repository_metadata(path, language, symbol.get("start_line"), symbol.get("end_line"), parser),
                "class_name": name,
                "stable_symbol_id": symbol.get("stable_symbol_id"),
                "file": path,
                "language": language,
                "file_imports": imports,
                "used_imports": self._used_imports(imports, class_usage),
                "methods": methods,
                "constructor": symbol.get("constructor"),
                "fields": symbol.get("fields", []),
                "decorators": symbol.get("decorators", []),
                "visibility": symbol.get("visibility"),
                "parent_class": (symbol.get("parent_classes") or [None])[0],
                "parent_classes": symbol.get("parent_classes", []),
                "implemented_interfaces": symbol.get("implemented_interfaces", []),
                "calls": class_calls,
                "references": class_references,
                "exports": [name] if symbol.get("is_exported") else [],
            },
        )

    def _source_function_chunk(
        self, path, content, repository_file_id, language, parser, imports, symbol
    ) -> SemanticChunk:
        return SemanticChunk(
            repository_file_id=repository_file_id,
            path=path,
            chunk_type="function",
            source_type="source_code",
            title=symbol["name"],
            language=language,
            content=self._slice_lines(content, symbol.get("start_line"), symbol.get("end_line")),
            start_line=symbol.get("start_line"),
            end_line=symbol.get("end_line"),
            metadata={
                **self._repository_metadata(path, language, symbol.get("start_line"), symbol.get("end_line"), parser),
                "function_name": symbol["name"],
                "signature": symbol.get("signature"),
                "stable_symbol_id": symbol.get("stable_symbol_id"),
                "parent_class": symbol.get("parent_symbol"),
                "parameters": symbol.get("parameters", []),
                "return_type": symbol.get("return_type"),
                "decorators": symbol.get("decorators", []),
                "visibility": symbol.get("visibility"),
                "file": path,
                "language": language,
                "file_imports": imports,
                "used_imports": self._used_imports(
                    imports, symbol.get("calls", []) + symbol.get("references", [])
                ),
                "calls": symbol.get("calls", []),
                "references": symbol.get("references", []),
                "local_variables": symbol.get("local_variables", []),
                "exports": [symbol["name"]] if symbol.get("is_exported") else [],
            },
        )

    def _source_symbol_group_chunks(
        self, path, content, repository_file_id, language, parser, imports, symbols
    ) -> list[SemanticChunk]:
        groups = {
            "constants": {"constant", "variable"},
            "types": {"interface", "type", "enum"},
        }
        chunks: list[SemanticChunk] = []
        for chunk_type, kinds in groups.items():
            group_symbols = [symbol for symbol in symbols if symbol.get("kind") in kinds]
            if not group_symbols:
                continue
            start_line = min(symbol.get("start_line", 1) for symbol in group_symbols)
            end_line = max(symbol.get("end_line", start_line) for symbol in group_symbols)
            chunks.append(
                SemanticChunk(
                    repository_file_id=repository_file_id,
                    path=path,
                    chunk_type=chunk_type,
                    source_type="source_code",
                    title=f"{Path(path).name} {chunk_type}",
                    language=language,
                    content=self._slice_lines(content, start_line, end_line),
                    start_line=start_line,
                    end_line=end_line,
                    metadata={
                        **self._repository_metadata(path, language, start_line, end_line, parser),
                        "symbols": group_symbols,
                        "imports": imports,
                        "file_imports": imports,
                        "used_imports": self._used_imports(
                            imports,
                            [
                                value
                                for symbol in group_symbols
                                for value in symbol.get("references", []) + symbol.get("calls", [])
                            ],
                        ),
                        "exports": [
                            symbol["name"]
                            for symbol in group_symbols
                            if symbol.get("is_exported")
                        ],
                    },
                )
            )
        return chunks

    def _build_documentation_chunks(self, path, content, items) -> list[SemanticChunk]:
        chunks = []
        for item in items:
            if item.item_type != "document_section":
                continue
            heading = item.data.get("heading", {})
            chunks.append(
                SemanticChunk(
                    repository_file_id=item.repository_file_id,
                    path=path,
                    chunk_type="documentation_section",
                    source_type="documentation",
                    title=heading.get("title") or item.name or path,
                    language="Markdown",
                    content=self._slice_lines(content, item.data.get("start_line"), item.data.get("end_line")),
                    start_line=item.data.get("start_line"),
                    end_line=item.data.get("end_line"),
                    metadata={
                        **self._repository_metadata(path, "Markdown", item.data.get("start_line"), item.data.get("end_line"), "markdown"),
                        "heading": heading.get("title"), "heading_level": heading.get("level"),
                        "section_depth": heading.get("level"), "slug": heading.get("slug"),
                        "outbound_links": self._section_links(content, item.data.get("start_line"), item.data.get("end_line")),
                        "code_blocks": self._section_code_blocks(content, item.data.get("start_line"), item.data.get("end_line")),
                        "tables_present": "|" in self._slice_lines(content, item.data.get("start_line"), item.data.get("end_line")),
                        "images_present": "![" in self._slice_lines(content, item.data.get("start_line"), item.data.get("end_line")),
                    },
                )
            )
        return chunks

    def _build_prisma_chunks(self, path, content, items) -> list[SemanticChunk]:
        enums = [item.data.get("name") for item in items if item.item_type == "prisma_enum"]
        return [
            SemanticChunk(
                repository_file_id=item.repository_file_id,
                path=path,
                chunk_type="prisma_model",
                source_type="database_schema",
                title=item.name or item.data["name"],
                language="Prisma",
                content=self._slice_lines(content, item.data.get("start_line"), item.data.get("end_line")),
                start_line=item.data.get("start_line"),
                end_line=item.data.get("end_line"),
                metadata={
                    **self._repository_metadata(path, "Prisma", item.data.get("start_line"), item.data.get("end_line"), "prisma"),
                    "model_name": item.data.get("name"), "fields": item.data.get("fields", []),
                    "relations": item.data.get("relations", []), "indexes": item.data.get("indexes", []),
                    "constraints": item.data.get("constraints", []), "enums": enums, "file": path,
                },
            )
            for item in items
            if item.item_type == "prisma_model"
        ]

    def _build_configuration_chunks(self, path, content, items) -> list[SemanticChunk]:
        return [
            SemanticChunk(
                repository_file_id=item.repository_file_id,
                path=path,
                chunk_type="configuration",
                source_type="configuration",
                title=item.name or path,
                language=self._configuration_language(path),
                content=content,
                start_line=1,
                end_line=max(1, len(content.splitlines())),
                metadata={
                    **self._repository_metadata(path, self._configuration_language(path), 1, max(1, len(content.splitlines())), "configuration"),
                    **item.data,
                    **self._configuration_tooling(item.data),
                },
            )
            for item in items
        ]

    def _read_file(self, repository_path: Path, path: str) -> str | None:
        root = repository_path.resolve()
        file_path = (root / path).resolve()
        try:
            file_path.relative_to(root)
            return file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            return None

    def _slice_lines(self, content: str, start_line: int | None, end_line: int | None) -> str:
        if start_line is None or end_line is None:
            return content
        return "\n".join(content.splitlines()[max(0, start_line - 1) : end_line])

    def _configuration_language(self, path: str) -> str:
        filename = Path(path).name
        if filename.endswith(".json"):
            return "JSON"
        if filename.endswith(".toml"):
            return "TOML"
        if filename.endswith((".yml", ".yaml")):
            return "YAML"
        return "Dockerfile" if "dockerfile" in filename.lower() else "Text"

    def _repository_metadata(self, path, language, start_line, end_line, parser: str | None = None) -> dict:
        return {
            "repository_id": self._repository_id,
            "path": path,
            "file": path,
            "repository_relative_path": path,
            "module": self._module_name(path),
            "language": language,
            "parser": parser,
            "start_line": start_line,
            "end_line": end_line,
            "relationships": self._empty_relationships(),
        }

    def _used_imports(self, imports: list[dict], values: list[str]) -> list[str]:
        used_names = set()
        for value in values:
            used_names.update(re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", value))
        used = []
        for import_item in imports:
            candidates = import_item.get("items", []) + [import_item.get("source")]
            for candidate in candidates:
                if candidate and candidate.split(".")[-1] in used_names and candidate not in used:
                    used.append(candidate)
        return used

    def _unique_values(self, values) -> list[str]:
        return list(dict.fromkeys(values))

    def _specialized_source_file_type(self, path: str, content: str, symbols: list[dict]) -> str:
        kinds = {symbol.get("kind") for symbol in symbols}
        if kinds & {"interface", "type", "enum"}:
            return "types"
        if kinds & {"constant", "variable"}:
            return "constants"
        if re.search(r"@(app|router)\.|\.(get|post|put|delete)\(", content):
            return "routes"
        if "config" in Path(path).stem.lower():
            return "configuration"
        return "source_file"

    def _section_links(self, content: str, start_line: int | None, end_line: int | None) -> list[dict]:
        section = self._slice_lines(content, start_line, end_line)
        return [{"text": match.group(1), "target": match.group(2)} for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", section)]

    def _section_code_blocks(self, content: str, start_line: int | None, end_line: int | None) -> list[dict]:
        section = self._slice_lines(content, start_line, end_line)
        blocks = []
        for match in re.finditer(r"```([^\n]*)\n(.*?)```", section, flags=re.DOTALL):
            language = match.group(1).strip().split(maxsplit=1)
            blocks.append({"language": language[0] if language else None, "content": match.group(2)})
        return blocks

    def _configuration_tooling(self, data: dict) -> dict:
        dependencies = {str(item).lower() for item in data.get("dependencies", [])}
        dependencies.update(str(item).lower() for item in data.get("dependency_groups", {}).get("devDependencies", {}))
        scripts = data.get("scripts", {})
        return {
            "frameworks": data.get("frameworks", []),
            "runtime": data.get("runtime"),
            "package_manager": data.get("package_manager"),
            "build_tool": self._first_tool(dependencies, scripts, {"vite": "Vite", "next": "Next.js", "webpack": "Webpack", "tsc": "TypeScript"}),
            "testing_framework": self._first_tool(dependencies, scripts, {"pytest": "Pytest", "jest": "Jest", "vitest": "Vitest"}),
            "linting_tools": self._matching_tools(dependencies, scripts, {"eslint": "ESLint", "ruff": "Ruff", "pylint": "Pylint"}),
            "formatter": self._first_tool(dependencies, scripts, {"prettier": "Prettier", "black": "Black", "ruff": "Ruff"}),
        }

    def _first_tool(self, dependencies, scripts, tools):
        matches = self._matching_tools(dependencies, scripts, tools)
        return matches[0] if matches else None

    def _matching_tools(self, dependencies, scripts, tools):
        script_text = " ".join(str(value).lower() for value in scripts.values())
        return [label for package, label in tools.items() if package in dependencies or package in script_text]

    def _module_name(self, path: str) -> str:
        suffixless = str(Path(path).with_suffix(""))
        return suffixless.replace("/__init__", "").replace("/", ".")

    def _empty_relationships(self) -> dict:
        return {key: [] for key in ("calls", "called_by", "imports", "imported_by", "inherits", "implements", "references", "exports")}

    def _resolve_relationships(self, chunks: list[SemanticChunk]) -> None:
        definitions: dict[str, list[dict]] = defaultdict(list)
        chunks_by_stable_id: dict[str, SemanticChunk] = {}
        chunks_by_path: dict[str, list[SemanticChunk]] = defaultdict(list)
        module_paths = {self._module_name(chunk.path): chunk.path for chunk in chunks}

        for chunk in chunks:
            metadata = chunk.metadata
            metadata.setdefault("stable_symbol_id", self._chunk_stable_id(chunk))
            chunks_by_path[chunk.path].append(chunk)
            stable_id = metadata.get("stable_symbol_id")
            if stable_id:
                definition = {"symbol": chunk.title, "path": chunk.path, "stable_symbol_id": stable_id, "chunk": chunk}
                definitions[chunk.title].append(definition)
                chunks_by_stable_id[stable_id] = chunk
            for method in metadata.get("methods", []):
                if method.get("stable_symbol_id"):
                    definitions[method["name"]].append(
                        {
                            "symbol": method["name"], "path": chunk.path,
                            "stable_symbol_id": method["stable_symbol_id"], "chunk": chunk,
                        }
                    )
            for symbol in metadata.get("symbols", []):
                if symbol.get("stable_symbol_id"):
                    definitions[symbol["name"]].append(
                        {
                            "symbol": symbol["name"],
                            "path": chunk.path,
                            "stable_symbol_id": symbol["stable_symbol_id"],
                            "chunk": chunk,
                        }
                    )

        for chunk in chunks:
            metadata = chunk.metadata
            relationships = metadata["relationships"]
            imported_paths: set[str] = set()
            relationships["exports"] = metadata.get("exports", [])
            relationships["inherits"] = metadata.get("parent_classes", [])
            relationships["implements"] = metadata.get("implemented_interfaces", [])

            for import_item in metadata.get("file_imports", metadata.get("imports", [])):
                source = import_item.get("source")
                target_path = self._resolve_import_path(source, chunk.path, module_paths)
                if target_path:
                    imported_paths.add(target_path)
                    relation = {"symbol": source, "path": target_path}
                    imported_symbol = self._resolve_imported_symbol(import_item, definitions, target_path)
                    if imported_symbol:
                        relation.update({
                            "symbol": imported_symbol["symbol"],
                            "stable_symbol_id": imported_symbol["stable_symbol_id"],
                        })
                    relationships["imports"].append(relation)
                    for target in chunks_by_path[target_path]:
                        target.metadata["relationships"]["imported_by"].append({"path": chunk.path})

            for call in metadata.get("calls", []):
                target = self._resolve_symbol(call, definitions, imported_paths, chunk.path)
                relation = {"symbol": call}
                if target:
                    relation.update({"path": target["path"], "stable_symbol_id": target["stable_symbol_id"]})
                    target["chunk"].metadata["relationships"]["called_by"].append(
                        {"symbol": metadata.get("stable_symbol_id") or chunk.title, "path": chunk.path}
                    )
                relationships["calls"].append(relation)

            for reference in metadata.get("references", []):
                target = self._resolve_symbol(reference, definitions, imported_paths, chunk.path)
                relation = {"symbol": reference}
                if target:
                    relation.update({"path": target["path"], "stable_symbol_id": target["stable_symbol_id"]})
                relationships["references"].append(relation)

    def _resolve_symbol(
        self,
        value: str,
        definitions: dict[str, list[dict]],
        imported_paths: set[str],
        current_path: str,
    ) -> dict | None:
        name = value.split(".")[-1]
        candidates = definitions.get(name, [])
        local_candidates = [candidate for candidate in candidates if candidate["path"] == current_path]
        if len(local_candidates) == 1:
            return local_candidates[0]
        imported_candidates = [candidate for candidate in candidates if candidate["path"] in imported_paths]
        return imported_candidates[0] if len(imported_candidates) == 1 else None

    @staticmethod
    def _resolve_imported_symbol(
        import_item: dict, definitions: dict[str, list[dict]], target_path: str
    ) -> dict | None:
        items = import_item.get("items", [])
        if not isinstance(items, list):
            return None
        for item in reversed(items):
            if not isinstance(item, str):
                continue
            candidates = [candidate for candidate in definitions.get(item, []) if candidate["path"] == target_path]
            if len(candidates) == 1:
                return candidates[0]
        return None

    def _resolve_import_path(self, source: str | None, current_path: str, module_paths: dict[str, str]) -> str | None:
        if not source:
            return None
        if source.startswith("."):
            # Resolve JavaScript/TypeScript relative imports from the importing file,
            # not by stripping leading dots. For example, ../../../../lib/api from
            # apps/web/app/repositories/[id]/search/page.tsx targets apps/web/lib/api.
            relative_path = posixpath.normpath(posixpath.join(posixpath.dirname(current_path), source))
            module = self._module_name(relative_path)
            return module_paths.get(module)
        return module_paths.get(source) or module_paths.get(source.replace("/", "."))

    def _chunk_stable_id(self, chunk: SemanticChunk) -> str:
        title = re.sub(r"[^A-Za-z0-9_$]+", "_", chunk.title).strip("_") or chunk.chunk_type
        return f"{chunk.path}::{title}"
