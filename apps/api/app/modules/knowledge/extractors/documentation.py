from __future__ import annotations

import re
from dataclasses import dataclass

from app.db.models.repository_file import RepositoryFile
from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.service import KnowledgeExtractionContext, KnowledgeItem


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_FENCE_PATTERN = re.compile(r"^```(\S*)\s*$")


@dataclass(frozen=True)
class MarkdownSection:
    heading: dict
    start_line: int
    end_line: int
    content_preview: str


class DocumentationKnowledgeExtractor:
    name = "documentation"

    def extract(self, context: KnowledgeExtractionContext) -> list[KnowledgeItem]:
        items: list[KnowledgeItem] = []
        for file in context.files:
            if file.is_binary or (file.extension or "").lower() not in {"md", "markdown"}:
                continue

            file_path = context.repository_path / file.path
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            metadata, body = self._extract_front_matter(text)
            headings = self._extract_headings(body)
            links = self._extract_links(body)
            code_blocks = self._extract_code_blocks(body)
            sections = self._extract_sections(body, headings)
            title = self._title_from_metadata(metadata, headings, file.path)

            items.append(
                KnowledgeItem(
                    repository_file_id=file.id,
                    path=file.path,
                    source_type=RepositoryKnowledgeSourceType.DOCUMENTATION,
                    item_type="document",
                    name=title,
                    extractor=self.name,
                    data={
                        "title": title,
                        "metadata": metadata,
                        "heading_count": len(headings),
                        "link_count": len(links),
                        "code_block_count": len(code_blocks),
                        "headings": headings,
                        "links": links,
                        "code_blocks": code_blocks,
                    },
                )
            )

            for section in sections:
                items.append(
                    KnowledgeItem(
                        repository_file_id=file.id,
                        path=file.path,
                        source_type=RepositoryKnowledgeSourceType.DOCUMENTATION,
                        item_type="document_section",
                        name=section.heading["title"],
                        extractor=self.name,
                        data={
                            "heading": section.heading,
                            "start_line": section.start_line,
                            "end_line": section.end_line,
                            "content_preview": section.content_preview,
                        },
                    )
                )

        return items

    def _extract_front_matter(self, text: str) -> tuple[dict, str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, text

        metadata: dict[str, str] = {}
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                # Preserve source line positions after front matter is removed.
                return metadata, "\n" * (index + 1) + "\n".join(lines[index + 1 :])
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"').strip("'")
        return {}, text

    def _extract_headings(self, text: str) -> list[dict]:
        headings: list[dict] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = HEADING_PATTERN.match(line)
            if not match:
                continue
            title = match.group(2).strip()
            headings.append(
                {
                    "level": len(match.group(1)),
                    "title": title,
                    "slug": self._slugify(title),
                    "line": line_number,
                }
            )
        return headings

    def _extract_links(self, text: str) -> list[dict]:
        links: list[dict] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                links.append(
                    {
                        "text": match.group(1),
                        "target": match.group(2),
                        "line": line_number,
                    }
                )
        return links

    def _extract_code_blocks(self, text: str) -> list[dict]:
        blocks: list[dict] = []
        open_block: dict | None = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = CODE_FENCE_PATTERN.match(line)
            if not match:
                continue
            if open_block is None:
                fence_info = (match.group(1) or "").split(maxsplit=1)
                language = fence_info[0] if fence_info else None
                open_block = {"language": language, "start_line": line_number}
            else:
                open_block["end_line"] = line_number
                blocks.append(open_block)
                open_block = None
        if open_block is not None:
            open_block["end_line"] = None
            blocks.append(open_block)
        return blocks

    def _extract_sections(self, text: str, headings: list[dict]) -> list[MarkdownSection]:
        if not headings:
            return []

        lines = text.splitlines()
        sections: list[MarkdownSection] = []
        for index, heading in enumerate(headings):
            start_line = heading["line"]
            end_line = headings[index + 1]["line"] - 1 if index + 1 < len(headings) else len(lines)
            content = "\n".join(lines[start_line:end_line]).strip()
            sections.append(
                MarkdownSection(
                    heading=heading,
                    start_line=start_line,
                    end_line=end_line,
                    content_preview=content[:1000],
                )
            )
        return sections

    def _title_from_metadata(self, metadata: dict, headings: list[dict], fallback: str) -> str:
        if metadata.get("title"):
            return metadata["title"]
        for heading in headings:
            if heading["level"] == 1:
                return heading["title"]
        return fallback

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "section"
