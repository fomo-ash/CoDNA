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
from app.modules.graph.schemas import RepositoryImpactTraversalResponse
from app.modules.graph.service import RepositoryGraphService
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
        graph_service: RepositoryGraphService | None = None,
    ) -> None:
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.provider = provider
        self.usage_tracker = usage_tracker or DatabaseAnswerUsageTracker(settings)
        self.answer_cache = answer_cache or DatabaseAnswerCache()
        self.graph_service = graph_service or RepositoryGraphService()

    async def ask(
        self, session: AsyncSession, repository_id: UUID, owner_id: UUID, question: str,
        impact_path: str | None = None, impact_depth: int = 2,
    ) -> RepositoryQuestionResponse:
        traversal: RepositoryImpactTraversalResponse | None = None
        if impact_path:
            traversal = await self.graph_service.traverse_impact(
                session, repository_id, owner_id, impact_path, impact_depth
            )
        elif cached := await self.answer_cache.get(session, repository_id, owner_id, question):
            return cached
        if traversal is not None:
            results = await self._impact_evidence(session, repository_id, [], traversal)
            vector_search_used = False
        else:
            retrieval = await self.retrieval_service.search(
                session=session,
                repository_id=repository_id,
                owner_id=owner_id,
                query=question,
                source_type=None,
                chunk_type=None,
                limit=self.settings.answer_max_context_chunks,
            )
            vector_search_used = retrieval.vector_search_used
            if not retrieval.results:
                return RepositoryQuestionResponse(
                    repository_id=repository_id,
                    question=question,
                    answer="I could not find enough indexed repository evidence to answer that question.",
                    citations=[],
                    vector_search_used=vector_search_used,
                )
            results = await self._expand_related_evidence(session, repository_id, retrieval.results)
        if not results:
            return RepositoryQuestionResponse(
                repository_id=repository_id,
                question=question,
                answer="I could not find enough indexed repository evidence to answer that question.",
                citations=[],
                vector_search_used=vector_search_used,
            )
        citations = self._citations(results)

        maximum_cost = self._maximum_cost()
        reservation = await self.usage_tracker.reserve(
            session, owner_id, repository_id, self.settings.answer_provider, self.settings.answer_model, maximum_cost
        )
        try:
            generation = await (self.provider or self._provider()).answer(self._prompt(question, results, traversal))
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
            vector_search_used=vector_search_used,
        )
        if traversal is None:
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

    async def _impact_evidence(
        self,
        session: AsyncSession,
        repository_id: UUID,
        results: Sequence[RepositorySearchResult],
        traversal: RepositoryImpactTraversalResponse,
    ) -> list[RepositorySearchResult]:
        """Limit impact explanations to the target and graph-confirmed dependents."""
        allowed_paths = [traversal.path, *traversal.affected_paths]
        allowed_set = set(allowed_paths)
        selected = [result for result in results if result.chunk.path in allowed_set]
        existing_ids = {result.chunk.id for result in selected}
        rows = await session.execute(
            select(RepositoryChunk)
            .where(
                RepositoryChunk.repository_id == repository_id,
                RepositoryChunk.path.in_(allowed_paths),
            )
            .order_by(RepositoryChunk.path, RepositoryChunk.start_line, RepositoryChunk.id)
        )
        selected.extend(
            RepositorySearchResult(
                chunk=RepositoryChunkRead.model_validate(chunk), score=0, lexical_score=0, vector_score=None
            )
            for chunk in rows.scalars()
            if chunk.id not in existing_ids
        )
        return selected

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

    def _prompt(
        self,
        question: str,
        results: Sequence[RepositorySearchResult],
        traversal: RepositoryImpactTraversalResponse | None = None,
    ) -> str:
        remaining = self.settings.answer_max_context_characters
        evidence: list[str] = []
        included_imports_for_paths: set[str] = set()
        for index, result in enumerate(results, start=1):
            chunk = result.chunk
            header = (
                f"[{index}] {chunk.path}:{chunk.start_line or 1}-{chunk.end_line or chunk.start_line or 1} "
                f"— {chunk.title} (source={chunk.source_type}, kind={chunk.chunk_type})\n"
            )
            available = remaining - len(header)
            if available <= 0:
                break
            import_context = ""
            if chunk.path not in included_imports_for_paths:
                statements = self._file_import_statements(chunk.metadata)
                if statements:
                    import_context = f"File-level imports:\n{chr(10).join(statements)}\n\n"
                    included_imports_for_paths.add(chunk.path)
            relationship_context = self._relationship_context(chunk.metadata)
            if relationship_context:
                relationship_context = f"Resolved relationships:\n{relationship_context}\n\n"
            content = f"{relationship_context}{import_context}{chunk.content}"[:available]
            evidence.append(f"{header}{content}")
            remaining -= len(header) + len(content)
        traversal_context = self._traversal_context(traversal)
        focus_instruction = (
            "This is not an impact request. Answer only the question asked. Do not add impact, risk, "
            "validation, or broad repository context unless the question explicitly requests it. Cite only "
            "evidence that directly supports a factual claim; omit unrelated retrieved evidence."
            if traversal is None
            else "This is an impact request. Follow the supplied impact traversal exactly."
        )
        return f"""You are CodeDNA, an experienced senior software engineer reviewing a codebase. You are provided a bounded set of retrieved source code, documentation, tests, configuration, and resolved repository relationships. Produce a repository review, not a retrieval summary. Every conclusion must be grounded in the evidence below.

{focus_instruction}

Before writing, classify the question internally as one primary category: Implementation, Execution Flow, Configuration, Architecture, API Explanation, Symbol Explanation, Module Explanation, Repository Layout, Dependency Analysis, Impact Analysis, Root Cause Analysis, Comparison, Data Flow, or Request Flow. Do not reveal this classification. Select the response structure that fits the category; never force an ordinary question into a universal template.

Reason across evidence instead of describing chunks one at a time. Connect implementation, documentation, tests, resolved imports, callers, callees, references, and graph relationships when they jointly establish a conclusion. Explain why a component is arranged or invoked as it is when the evidence supports that reasoning. Prefer "X invokes Y after Z" over "X contains Y." Do not repeat the same fact in multiple sections.

For implementation, symbol, or module questions, trace the application's entry point and active execution path when possible: where execution enters, why that entry is reached, construction or registration, callers, control transfer, returned value or side effect, and what happens next. If a caller, registration point, or later step is absent from the evidence, say that exact link is not established rather than inventing it.

For execution, request, and data-flow questions, present the proven runtime path as a compact vertical flow (for example, `Client → API → handler → service → storage`) followed by the important transitions and their purpose. Include only observed steps; do not turn an import list into a runtime flow.

For configuration questions, explain the composition root, initialization order, registration, dependency injection, environment inputs, and middleware ordering only where evidenced. State why an ordering constraint matters only if the registration or behavior evidence establishes it.

For architecture questions, explain responsibilities, ownership, module boundaries, dependency direction, and communication. Include a small ASCII diagram only when at least three grounded components and their relationships make it clearer. Distinguish implemented runtime behavior from documented or planned architecture.

For API questions, connect the API surface to implementation and tests when those evidence types are present. State whether they agree, whether a test demonstrates behavior absent from documentation, or whether a document is intent rather than runtime behavior—only when the evidence makes that comparison possible.

For root-cause questions, use `Observed Behavior`, `Root Cause`, `Supporting Evidence`, and `Fix Strategy`. Diagnose from the supplied causal evidence; do not give generic debugging checklists.

For repository-layout questions, show only grounded paths in a compact fenced tree. Label any partial tree `Relevant observed subtree`; never call it the repository structure or a complete tree unless the evidence enumerates it.

When multiple evidence types support a genuine engineering observation, include a concise `## Repository Insights` section with two to four non-obvious insights. Do not force this section, and do not use it to restate file contents. Good insights explain properties such as ownership boundaries, registration order, isolation, missing coverage, or the difference between documented intent and runtime behavior.

When the question asks for a change-impact analysis of a file or symbol, treat supplied impact-traversal paths and resolved repository relationships as the authoritative dependency graph. The impact traversal is the primary source of truth for dependency propagation: use the dependency graph before retrieved code, use its dependency paths to explain why each file is affected, and always walk every path in order. A path `A -> B` means that B depends on A, so a change propagates from A to B; never reverse that direction or combine separate paths into a new chain. For every affected file, find its exact listed dependency path, explain how the change propagates along that path, and use retrieved code only to explain the established relationship. Discuss every file listed in affected_paths unless the traversal lacks sufficient information, in which case say so explicitly. Do not replace traversal evidence with independent reasoning from retrieved code or unrelated repository evidence. When dependency paths are supplied, structure the explanation around those exact paths. Begin with the requested item's responsibility, then use exactly these sections: "## Summary", "## Direct Impact", "## Transitive Impact", "## Risk Assessment", and "## Recommended Validation". Separate one-hop dependents from downstream dependents. Explain every dependency path in order, why each file is affected, the connecting API, class, function, or component contract when the evidence identifies it, and the likely behavior change. Merge shared path segments rather than repeating them. Label relationships as imports, calls, renders, references, or inheritance only when that relationship type is supplied. State the impact risk as low, medium, or high and recommend targeted files, tests, or execution paths to validate. If the traversal depth is limited, explicitly say that further downstream impacts may exist. Do not invent dependencies or relationship types that are absent from the evidence.

If an impact traversal has no affected_paths and no dependency_paths, lead with: "No downstream dependency is established by the indexed graph." In that case, do not treat documentation, TypeScript compilation scope, architecture diagrams, or a target file's intended boundary as a direct or transitive dependency. Documentation may appear only as clearly labelled context in Direct Impact, never as proof that a page, component, gateway, or call site is affected. If the target's source implementation is not in the evidence, say that its direct runtime behavior cannot be assessed; do not substitute a design document for it. Use an uncertainty-aware risk statement such as "direct-change risk is unknown from source evidence; repository-wide blast radius is unverified." Do not describe one retrieved consumer as the complete consumer set unless the traversal proves completeness.

For an impact request, only files in the supplied affected_paths are impact candidates. A file imported by the requested path is context about what that file depends on, not an affected file, unless it is also in affected_paths.

Prefer resolved repository-local relationships. Ignore unresolved built-in, standard-library, collection, and language-runtime relationships such as len, sum, print, append, random.choice, or method helpers unless the question specifically asks about them. Never infer a relationship that is absent from the supplied evidence.

Never invent files, code, behavior, relationships, or dead-code claims. If the repository does not establish a relationship, explicitly state that the available evidence is insufficient, then give the strongest grounded conclusion.

For questions about repository layout, package organization, or directory hierarchy, include a compact fenced plain-text tree after the summary when the supplied evidence supports it. Include only grounded paths and use an ellipsis for intentionally incomplete branches.

Response contract — highest priority:
- Lead with the direct answer. Do not restate the question or add generic framing.
- Prefer retrieved source code and resolved relationships over planning documents. When only documentation is available, say the conclusion is documented intent rather than active runtime behavior.
- Make each factual claim traceable with adjacent evidence markers such as [1] or [1][2]. Do not claim an implementation is active, unique, or complete unless the evidence proves it.
- Treat evidence scope as a first-class constraint. Describe only files, symbols, routes, and relationships present in the evidence. If showing a partial tree, label it "Relevant observed subtree" (or equivalent), never "Repository structure" or "complete structure" unless the evidence enumerates the whole tree.
- Use an adaptive structure. For ordinary implementation questions, prefer `## Overview`, `## Execution Flow`, `## Key Components`, optional `## Repository Insights`, and `## Evidence Boundary`. For configuration, architecture, API, and root-cause questions, use the category-specific structures above. Omit empty sections.
- Do not call a dependency, component, route, client, or implementation "shared", "central", "only", "active", "legacy", or "unused" unless an import, call, route registration, or other supplied relationship directly establishes that fact. Prefer precise language such as "the supplied evidence shows".
- For route-level evidence, explain the route subtree and its behavior; do not infer application-wide architecture, authentication behavior, or a complete dependency graph from that subtree alone.
- Use short Markdown headings and compact lists only when they make a multi-part answer easier to scan. Do not add `Direct Impact`, `Transitive Impact`, `Risk Assessment`, or `Recommended Validation` unless the question is explicitly an impact, risk, validation, or dependency request. For a simple repository-purpose question, give a concise product summary, separate implemented behavior from documented direction, and finish with the evidence boundary—nothing more.
- For repository-layout questions, include a compact fenced plain-text tree using only grounded paths. For all other questions, do not add a tree unless it materially clarifies the answer.
- For explicit impact requests, follow the required impact sections above. For ordinary explanation questions, stay focused and avoid a change plan.
- If evidence is incomplete, state exactly what is missing and give the strongest supported conclusion. Never fill gaps with planned, legacy, or assumed architecture.
- Do not add a standalone `Evidence` heading. Use inline citations and the required `Evidence Boundary` section when scope is incomplete.
- Keep normal answers under 500 words unless the question explicitly asks for detail. Write naturally and avoid boilerplate such as "the supplied evidence shows" or "the implementation indicates" when a direct statement is possible.

Question: {question}

{traversal_context}

Evidence:
{chr(10).join(evidence)}
"""

    @staticmethod
    def _traversal_context(traversal: RepositoryImpactTraversalResponse | None) -> str:
        if traversal is None:
            return ""
        affected_paths = ", ".join(traversal.affected_paths) or "(none)"
        dependency_paths = "\n".join(
            f"- {' -> '.join(path)}" for path in traversal.paths
        ) or "- (none)"
        return (
            "Authoritative impact traversal:\n"
            "- Path direction: A -> B means B depends on A; changes propagate from A to B.\n"
            f"- Target path: {traversal.path}\n"
            f"- Traversal depth: {traversal.depth}\n"
            f"- affected_paths: {affected_paths}\n"
            "- dependency_paths:\n"
            f"{dependency_paths}"
        )

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
    def _relationship_context(metadata: dict[str, object]) -> str:
        """Render only indexed, resolved relationships for the answer prompt."""
        relationships = metadata.get("relationships", {})
        if not isinstance(relationships, dict):
            return ""
        lines: list[str] = []
        labels = {
            "calls": "calls",
            "called_by": "called by",
            "imports": "imports",
            "imported_by": "imported by",
            "references": "references",
            "inherits": "inherits",
            "implements": "implements",
            "exports": "exports",
        }
        for key, label in labels.items():
            values = relationships.get(key)
            if not isinstance(values, list) or not values:
                continue
            rendered: list[str] = []
            for value in values[:8]:
                if isinstance(value, dict):
                    symbol = value.get("symbol")
                    path = value.get("path")
                    if isinstance(symbol, str) and isinstance(path, str):
                        rendered.append(f"{symbol} ({path})")
                    elif isinstance(path, str):
                        rendered.append(path)
                    elif isinstance(symbol, str):
                        rendered.append(symbol)
                elif isinstance(value, str):
                    rendered.append(value)
            if rendered:
                suffix = " …" if len(values) > len(rendered) else ""
                lines.append(f"- {label}: {', '.join(rendered)}{suffix}")
        return "\n".join(lines)

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
