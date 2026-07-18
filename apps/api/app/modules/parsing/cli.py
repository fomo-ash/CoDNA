from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.modules.parsing.results import parse_result_to_dict
from app.modules.parsing.service import RepositoryParserServiceImpl


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse repository files in an isolated process.")
    parser.add_argument("--repository-path", required=True)
    parser.add_argument("--files-json", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    repository_path = Path(args.repository_path)
    with Path(args.files_json).open("r", encoding="utf-8") as file:
        file_payload = json.load(file)

    files = [
        SimpleNamespace(
            id=UUID(item["id"]),
            path=item["path"],
            extension=item.get("extension"),
            language=item.get("language"),
            is_binary=item.get("is_binary", False),
        )
        for item in file_payload
    ]
    parse_result = RepositoryParserServiceImpl().parse_repository(repository_path, files)

    with Path(args.output_json).open("w", encoding="utf-8") as file:
        json.dump(parse_result_to_dict(parse_result), file)


if __name__ == "__main__":
    main()
