from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models.repository_chunk import RepositoryChunk
from app.modules.chunks.schemas import RepositoryChunkRead
from app.modules.embeddings.service import EmbeddingConfigurationError
from app.modules.questions.budget import AnswerUsageTracker, DatabaseAnswerUsageTracker
from app.modules.questions.cache import AnswerCache, DatabaseAnswerCache
from app.modules.questions.schemas import (
    RepositoryAnswerCitation,
    RepositoryQuestionResponse,
)
from app.modules.retrieval.schemas import RepositorySearchResult
from app.modules.retrieval.service import RepositoryRetrievalService


class AnswerProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class AnswerGeneration:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class AnswerProvider(Protocol):
    async def answer(self, prompt: str) -> AnswerGeneration: ...


class GoogleAnswerProvider:
    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens

    async def answer(self, prompt: str) -> AnswerGeneration:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    endpoint,
                    headers={"x-goog-api-key": self.api_key},
                    json={
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": self.max_output_tokens,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AnswerProviderError("Answer provider quota or rate limit has been reached.", 429) from exc
            raise AnswerProviderError("Answer provider request failed.", exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise AnswerProviderError("Answer provider request failed.") from exc
        candidates = response.json().get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        answer = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not answer:
            raise AnswerProviderError("Answer provider returned an empty response.")
        usage = response.json().get("usageMetadata", {})
        return AnswerGeneration(
            text=answer,
            input_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0)),
        )


class OpenAIAnswerProvider:
    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens

    async def answer(self, prompt: str) -> AnswerGeneration:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_completion_tokens": self.max_output_tokens,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AnswerProviderError("Answer provider quota or rate limit has been reached.", 429) from exc
            raise AnswerProviderError("Answer provider request failed.", exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise AnswerProviderError("Answer provider request failed.") from exc
        choices = response.json().get("choices", [])
        answer = choices[0].get("message", {}).get("content", "").strip() if choices else ""
        if not answer:
            raise AnswerProviderError("Answer provider returned an empty response.")
        usage = response.json().get("usage", {})
        return AnswerGeneration(
            text=answer,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
        )


class RepositoryQuestionService:
    def __init__(
        self,
        settings: Settings,
        retrieval_service: RepositoryRetrievalService,
        provider: AnswerProvider | None = None,
        usage_tracker: AnswerUsageTracker | None = None,
        answer_cache: AnswerCache | None = None,
    ) -> None:
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.provider = provider
        self.usage_tracker = usage_tracker or DatabaseAnswerUsageTracker(settings)
        self.answer_cache = answer_cache or DatabaseAnswerCache()

    async def ask(
        self, session: AsyncSession, repository_id: UUID, owner_id: UUID, question: str
    ) -> RepositoryQuestionResponse:
        if cached := await self.answer_cache.get(session, repository_id, owner_id, question):
            return cached
        retrieval = await self.retrieval_service.search(
            session=session,
            repository_id=repository_id,
            owner_id=owner_id,
            query=question,
            source_type=None,
            chunk_type=None,
            limit=self.settings.answer_max_context_chunks,
        )
        if not retrieval.results:
            return RepositoryQuestionResponse(
                repository_id=repository_id,
                question=question,
                answer="I could not find enough indexed repository evidence to answer that question.",
                citations=[],
                vector_search_used=retrieval.vector_search_used,
            )

        results = await self._expand_related_evidence(session, repository_id, retrieval.results)
        citations = self._citations(results)

        maximum_cost = self._maximum_cost()
        reservation = await self.usage_tracker.reserve(
            session, owner_id, repository_id, self.settings.answer_provider, self.settings.answer_model, maximum_cost
        )
        try:
            generation = await (self.provider or self._provider()).answer(self._prompt(question, results))
        except Exception:
            await self.usage_tracker.finalize(session, reservation, 0, 0, Decimal("0"), "failed")
            raise
        actual_cost = self._cost_usd(generation.input_tokens, generation.output_tokens)
        await self.usage_tracker.finalize(
            session, reservation, generation.input_tokens, generation.output_tokens, actual_cost, "completed"
        )
        answer = generation.text
        citation_indices = self._citation_indices(answer, len(results))
        if not citation_indices:
            answer = f"{answer.rstrip()}\n\nEvidence: [1]"
            citation_indices = [1]
        answer, citations = self._rebase_citations(answer, citations, citation_indices)
        response = RepositoryQuestionResponse(
            repository_id=repository_id,
            question=question,
            answer=answer,
            citations=citations,
            vector_search_used=retrieval.vector_search_used,
        )
        await self.answer_cache.save(session, response)
        return response

    def _provider(self) -> AnswerProvider:
        if self.settings.answer_provider == "google":
            if not self.settings.google_api_key:
                raise EmbeddingConfigurationError("GOOGLE_API_KEY is required to answer repository questions.")
            return GoogleAnswerProvider(
                self.settings.google_api_key, self.settings.answer_model, self.settings.answer_max_output_tokens
            )
        if not self.settings.openai_api_key:
            raise EmbeddingConfigurationError("OPENAI_API_KEY is required to answer repository questions.")
        return OpenAIAnswerProvider(
            self.settings.openai_api_key, self.settings.answer_model, self.settings.answer_max_output_tokens
        )

    def _maximum_cost(self) -> Decimal:
        # A conservative reservation prevents a final response from exceeding the configured budget.
        maximum_input_tokens = self.settings.answer_max_context_characters // 4 + 1000
        return self._cost_usd(maximum_input_tokens, self.settings.answer_max_output_tokens)

    def _cost_usd(self, input_tokens: int, output_tokens: int) -> Decimal:
        prices = {
            ("openai", "gpt-5.4-mini"): (Decimal("0.75"), Decimal("4.50")),
            ("openai", "gpt-5.4-nano"): (Decimal("0.20"), Decimal("1.25")),
            ("openai", "gpt-5.4"): (Decimal("2.50"), Decimal("15.00")),
            ("google", "gemini-3.1-flash-lite"): (Decimal("0.25"), Decimal("1.50")),
        }
        try:
            input_price, output_price = prices[(self.settings.answer_provider, self.settings.answer_model)]
        except KeyError as exc:
            raise EmbeddingConfigurationError("No answer-cost policy is configured for the selected provider model.") from exc
        return (Decimal(input_tokens) * input_price + Decimal(output_tokens) * output_price) / Decimal(1_000_000)

    async def _expand_related_evidence(
        self, session: AsyncSession, repository_id: UUID, results: Sequence[RepositorySearchResult]
    ) -> list[RepositorySearchResult]:
        related_paths = self._related_paths(results)
        if not related_paths or self.settings.answer_max_related_chunks <= 0:
            return list(results)
        rows = await session.execute(
            select(RepositoryChunk)
            .where(RepositoryChunk.repository_id == repository_id, RepositoryChunk.path.in_(related_paths))
            .order_by(RepositoryChunk.path, RepositoryChunk.start_line, RepositoryChunk.id)
        )
        existing_ids = {result.chunk.id for result in results}
        related = [
            RepositorySearchResult(
                chunk=RepositoryChunkRead.model_validate(chunk), score=0, lexical_score=0, vector_score=None
            )
            for chunk in rows.scalars()
            if chunk.id not in existing_ids
        ]
        return [*results, *related[: self.settings.answer_max_related_chunks]]

    @staticmethod
    def _related_paths(results: Sequence[RepositorySearchResult]) -> list[str]:
        paths: list[str] = []
        for result in results:
            relationships = result.chunk.metadata.get("relationships", {})
            for relationship_type in ("imports", "calls"):
                for relationship in relationships.get(relationship_type, []):
                    path = relationship.get("path") if isinstance(relationship, dict) else None
                    if isinstance(path, str) and path and path not in paths:
                        paths.append(path)
        return paths

    def _prompt(self, question: str, results: Sequence[RepositorySearchResult]) -> str:
        remaining = self.settings.answer_max_context_characters
        evidence: list[str] = []
        included_imports_for_paths: set[str] = set()
        for index, result in enumerate(results, start=1):
            chunk = result.chunk
            header = f"[{index}] {chunk.path}:{chunk.start_line or 1}-{chunk.end_line or chunk.start_line or 1} — {chunk.title}\n"
            available = remaining - len(header)
            if available <= 0:
                break
            import_context = ""
            if chunk.path not in included_imports_for_paths:
                statements = self._file_import_statements(chunk.metadata)
                if statements:
                    import_context = f"File-level imports:\n{chr(10).join(statements)}\n\n"
                    included_imports_for_paths.add(chunk.path)
            content = f"{import_context}{chunk.content}"[:available]
            evidence.append(f"{header}{content}")
            remaining -= len(header) + len(content)
        return f"""You are a repository-aware software assistant. Answer using only the supplied repository evidence.

Reason over the repository, not isolated facts. When several files describe similar functionality, trace the application's entry point, imports, component hierarchy, calls, and references to identify the active path. Clearly distinguish the active execution path from an alternate implementation; call code unused or unreachable only when the supplied relationships support that conclusion.

For execution or data-flow questions, explain the active flow in order. For architecture questions, cover execution flow, component hierarchy, data flow, state ownership, prop flow, and import relationships when they are relevant to the question. For impact questions, identify direct and indirect affected files, imports, exports, references, and runtime consequences when the evidence supports them.

Do not use generic phrases such as "the evidence does not show" or "I can't confirm" when a reasonable repository-level inference can be made from the supplied files. If something truly remains unknown, state the narrow missing detail and still give the strongest grounded conclusion. Do not invent files, code, behavior, relationships, or dead-code claims.

Write a concise, natural, and complete answer. For a requested change plan, use a compact numbered plan of at most six steps and at most two bullets per step. Include only files, variables, components, props, and runtime consequences that are affected; group unrelated components instead of listing them one by one. Finish the ordered plan before adding optional detail, and omit lower-value detail rather than leaving a section unfinished. Use short headings only when they improve a multi-part explanation. Cite factual claims with the evidence numbers, for example [1] or [1][2].

Question: {question}

Evidence:
{chr(10).join(evidence)}
"""

    @staticmethod
    def _citations(results: Sequence[RepositorySearchResult]) -> list[RepositoryAnswerCitation]:
        return [
            RepositoryAnswerCitation(
                index=index,
                chunk_id=result.chunk.id,
                path=result.chunk.path,
                start_line=result.chunk.start_line,
                end_line=result.chunk.end_line,
                title=result.chunk.title,
            )
            for index, result in enumerate(results, start=1)
        ]

    @staticmethod
    def _citation_indices(answer: str, result_count: int) -> list[int]:
        """Return valid, de-duplicated evidence markers in their answer order."""
        indices: list[int] = []
        for match in re.finditer(r"\[(\d+)\]", answer):
            index = int(match.group(1))
            if 1 <= index <= result_count and index not in indices:
                indices.append(index)
        return indices

    @staticmethod
    def _file_import_statements(metadata: dict[str, object]) -> list[str]:
        imports = metadata.get("file_imports", [])
        if not isinstance(imports, list):
            return []
        return [item["statement"] for item in imports if isinstance(item, dict) and isinstance(item.get("statement"), str)]

    @staticmethod
    def _rebase_citations(
        answer: str, citations: Sequence[RepositoryAnswerCitation], citation_indices: Sequence[int]
    ) -> tuple[str, list[RepositoryAnswerCitation]]:
        index_map = {original: rebased for rebased, original in enumerate(citation_indices, start=1)}
        rebased_answer = re.sub(
            r"\[(\d+)\]", lambda match: f"[{index_map.get(int(match.group(1)), match.group(1))}]", answer
        )
        citation_by_index = {citation.index: citation for citation in citations}
        return (
            rebased_answer,
            [
                citation_by_index[original].model_copy(update={"index": index_map[original]})
                for original in citation_indices
                if original in citation_by_index
            ],
        )
