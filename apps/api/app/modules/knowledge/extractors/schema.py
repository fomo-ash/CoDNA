from __future__ import annotations

import re

from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.service import KnowledgeExtractionContext, KnowledgeItem


BLOCK_PATTERN = re.compile(r"^(model|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", re.MULTILINE)
ATTRIBUTE_PATTERN = re.compile(r"(@@?\w+(?:\([^)]*\))?)")


class PrismaSchemaKnowledgeExtractor:
    name = "prisma_schema"

    def extract(self, context: KnowledgeExtractionContext) -> list[KnowledgeItem]:
        items: list[KnowledgeItem] = []
        for file in context.files:
            if file.is_binary or file.filename != "schema.prisma":
                continue

            file_path = context.repository_path / file.path
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            models, enums = self._parse_schema(text)
            items.append(
                KnowledgeItem(
                    repository_file_id=file.id,
                    path=file.path,
                    source_type=RepositoryKnowledgeSourceType.DATABASE_SCHEMA,
                    item_type="prisma_schema",
                    name=file.path,
                    extractor=self.name,
                    data={
                        "model_count": len(models),
                        "enum_count": len(enums),
                        "models": [model["name"] for model in models],
                        "enums": [enum["name"] for enum in enums],
                    },
                )
            )
            for model in models:
                items.append(
                    KnowledgeItem(
                        repository_file_id=file.id,
                        path=file.path,
                        source_type=RepositoryKnowledgeSourceType.DATABASE_SCHEMA,
                        item_type="prisma_model",
                        name=model["name"],
                        extractor=self.name,
                        data=model,
                    )
                )
            for enum in enums:
                items.append(
                    KnowledgeItem(
                        repository_file_id=file.id,
                        path=file.path,
                        source_type=RepositoryKnowledgeSourceType.DATABASE_SCHEMA,
                        item_type="prisma_enum",
                        name=enum["name"],
                        extractor=self.name,
                        data=enum,
                    )
                )
        return items

    def _parse_schema(self, text: str) -> tuple[list[dict], list[dict]]:
        models: list[dict] = []
        enums: list[dict] = []
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            match = re.match(r"^(model|enum)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", line)
            if not match:
                index += 1
                continue

            block_type, name = match.group(1), match.group(2)
            start_line = index + 1
            block_lines: list[str] = []
            index += 1
            while index < len(lines) and lines[index].strip() != "}":
                block_lines.append(lines[index])
                index += 1
            end_line = index + 1

            if block_type == "model":
                models.append(self._parse_model(name, block_lines, start_line, end_line))
            else:
                enums.append(self._parse_enum(name, block_lines, start_line, end_line))
            index += 1
        return models, enums

    def _parse_model(self, name: str, lines: list[str], start_line: int, end_line: int) -> dict:
        fields: list[dict] = []
        constraints: list[str] = []
        indexes: list[str] = []
        relations: list[dict] = []

        for offset, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("@@"):
                constraints.append(line)
                if line.startswith("@@index") or line.startswith("@@unique"):
                    indexes.append(line)
                continue

            parts = line.split()
            if len(parts) < 2:
                continue
            field = {
                "name": parts[0],
                "type": parts[1],
                "attributes": ATTRIBUTE_PATTERN.findall(line),
                "line": start_line + offset,
                "is_optional": parts[1].endswith("?"),
                "is_list": parts[1].endswith("[]"),
            }
            fields.append(field)
            if any(attribute.startswith("@relation") for attribute in field["attributes"]):
                relations.append(field)

        return {
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
            "fields": fields,
            "relations": relations,
            "indexes": indexes,
            "constraints": constraints,
        }

    def _parse_enum(self, name: str, lines: list[str], start_line: int, end_line: int) -> dict:
        values = [
            line.strip().split()[0]
            for line in lines
            if line.strip() and not line.strip().startswith("//") and not line.strip().startswith("@@")
        ]
        return {
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
            "values": values,
        }
