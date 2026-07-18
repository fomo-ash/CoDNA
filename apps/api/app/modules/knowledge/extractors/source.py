from __future__ import annotations

from app.modules.knowledge.enums import RepositoryKnowledgeSourceType
from app.modules.knowledge.service import KnowledgeExtractionContext, KnowledgeItem
from app.modules.parsing.enums import RepositoryFileParseStatus


class SourceCodeKnowledgeExtractor:
    name = "source_code"

    def extract(self, context: KnowledgeExtractionContext) -> list[KnowledgeItem]:
        if context.parse_result is None:
            return []

        items: list[KnowledgeItem] = []
        for parsed_file in context.parse_result.files:
            if parsed_file.status not in {
                RepositoryFileParseStatus.PARSED,
                RepositoryFileParseStatus.SYNTAX_ERROR,
            }:
                continue

            items.append(
                KnowledgeItem(
                    repository_file_id=parsed_file.repository_file_id,
                    path=parsed_file.path,
                    source_type=RepositoryKnowledgeSourceType.SOURCE_CODE,
                    item_type="source_file",
                    name=parsed_file.path,
                    extractor=self.name,
                    data={
                        "language": parsed_file.language,
                        "parser": parsed_file.parser,
                        "status": parsed_file.status.value,
                        "root_node_type": parsed_file.root_node_type,
                        "has_error": parsed_file.has_error,
                        "error_count": parsed_file.error_count,
                        "symbol_count": parsed_file.symbol_count,
                        "import_count": parsed_file.import_count,
                        "exports": [
                            symbol["name"] for symbol in parsed_file.symbols if symbol.get("is_exported")
                        ],
                    },
                    extracted_at=parsed_file.parsed_at,
                )
            )

            for symbol in parsed_file.symbols:
                items.append(
                    KnowledgeItem(
                        repository_file_id=parsed_file.repository_file_id,
                        path=parsed_file.path,
                        source_type=RepositoryKnowledgeSourceType.SOURCE_CODE,
                        item_type="symbol",
                        name=symbol.get("name"),
                        extractor=self.name,
                        data={
                            "language": parsed_file.language,
                            "parser": parsed_file.parser,
                            **symbol,
                        },
                        extracted_at=parsed_file.parsed_at,
                    )
                )

            for import_item in parsed_file.imports:
                items.append(
                    KnowledgeItem(
                        repository_file_id=parsed_file.repository_file_id,
                        path=parsed_file.path,
                        source_type=RepositoryKnowledgeSourceType.SOURCE_CODE,
                        item_type="import",
                        name=import_item.get("source") or import_item.get("statement"),
                        extractor=self.name,
                        data={
                            "language": parsed_file.language,
                            "parser": parsed_file.parser,
                            **import_item,
                        },
                        extracted_at=parsed_file.parsed_at,
                    )
                )

        return items
