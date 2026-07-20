from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.modules.chunks.schemas import RepositoryChunkRead
from app.modules.questions.service import AnswerGeneration, AnswerProviderError, RepositoryQuestionService
from app.modules.questions.schemas import RepositoryAnswerCitation
from app.modules.graph.schemas import RepositoryImpactTraversalResponse
from app.modules.retrieval.schemas import RepositorySearchResponse, RepositorySearchResult


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")


class FakeRetrievalService:
    def __init__(self, results: list[RepositorySearchResult]) -> None:
        self.results = results
        self.limit = None

    async def search(self, **kwargs) -> RepositorySearchResponse:
        self.limit = kwargs["limit"]
        return RepositorySearchResponse(
            repository_id=REPOSITORY_ID,
            query=kwargs["query"],
            results=self.results,
            vector_search_used=True,
        )


class FakeAnswerProvider:
    def __init__(self) -> None:
        self.prompt = None

    async def answer(self, prompt: str) -> AnswerGeneration:
        self.prompt = prompt
        return AnswerGeneration("`StudentLifeEnv` is defined in `environment.py`. [1]", 100, 20)


class FakeUsageTracker:
    def __init__(self) -> None:
        self.reservations = []
        self.finalized = []

    async def reserve(self, session, owner_id, repository_id, provider, model, maximum_cost):
        del session
        reservation = object()
        self.reservations.append((owner_id, repository_id, provider, model, maximum_cost, reservation))
        return reservation

    async def finalize(self, session, reservation, input_tokens, output_tokens, actual_cost, status):
        del session
        self.finalized.append((reservation, input_tokens, output_tokens, actual_cost, status))


class FakeAnswerCache:
    def __init__(self) -> None:
        self.cached = None
        self.saved = []

    async def get(self, session, repository_id, owner_id, question):
        del session, repository_id, owner_id, question
        return self.cached.model_copy(update={"cached": True}) if self.cached else None

    async def save(self, session, response):
        del session
        self.saved.append(response)
        self.cached = response


class FakeGraphService:
    async def traverse_impact(self, session, repository_id, owner_id, path, depth):
        del session, owner_id
        return RepositoryImpactTraversalResponse(
            repository_id=repository_id,
            path=path.strip(),
            depth=depth,
            affected_paths=["server/app.py"],
            paths=[[path.strip(), "main.py", "server/app.py"]],
        )


class FakeSession:
    def __init__(self, chunks):
        self.chunks = chunks

    async def execute(self, statement):
        del statement
        return SimpleNamespace(scalars=lambda: self.chunks)


def settings() -> SimpleNamespace:
    return SimpleNamespace(
        answer_max_context_chunks=2,
        answer_max_context_characters=500,
        answer_max_output_tokens=100,
        answer_provider="openai",
        answer_model="gpt-5.4-mini",
        google_api_key=None,
        openai_api_key=None,
        answer_budget_usd=4,
    )


def result(path: str = "environment.py", title: str = "StudentLifeEnv") -> RepositorySearchResult:
    now = datetime.now(UTC)
    return RepositorySearchResult(
        chunk=RepositoryChunkRead(
            id=uuid4(), repository_id=REPOSITORY_ID, repository_file_id=None,
            path=path, chunk_type="class", source_type="source_code", title=title,
            language="Python", content="class StudentLifeEnv: pass", start_line=6, end_line=12,
            metadata={}, created_at=now, updated_at=now,
        ),
        score=0.9, lexical_score=0.1, vector_score=0.9,
    )


def test_question_uses_bounded_retrieval_and_returns_citations() -> None:
    retrieval = FakeRetrievalService([result(), result("test_env.py", "test_env")])
    provider = FakeAnswerProvider()
    usage_tracker = FakeUsageTracker()
    answer_cache = FakeAnswerCache()
    service = RepositoryQuestionService(settings(), retrieval, provider, usage_tracker, answer_cache)

    response = asyncio.run(service.ask(object(), REPOSITORY_ID, OWNER_ID, "Where is StudentLifeEnv defined?"))

    assert retrieval.limit == 2
    assert response.answer == "`StudentLifeEnv` is defined in `environment.py`. [1]"
    assert [(citation.index, citation.path, citation.start_line) for citation in response.citations] == [
        (1, "environment.py", 6)
    ]
    assert "[1] environment.py:6-12" in provider.prompt
    assert "trace the application's entry point" in provider.prompt
    assert "active execution path" in provider.prompt
    assert "## Direct Impact" in provider.prompt
    assert "authoritative dependency graph" in provider.prompt
    assert "primary source of truth for dependency propagation" in provider.prompt
    assert "always walk every path in order" in provider.prompt
    assert "Discuss every file listed in affected_paths" in provider.prompt
    assert "structure the explanation around those exact paths" in provider.prompt
    assert "never reverse that direction" in provider.prompt
    assert "You are CodeDNA" in provider.prompt
    assert "Treat evidence scope as a first-class constraint" in provider.prompt
    assert "Relevant observed subtree" in provider.prompt
    assert "Do not call a dependency, component, route, client, or implementation" in provider.prompt
    assert "No downstream dependency is established by the indexed graph" in provider.prompt
    assert "do not treat documentation, TypeScript compilation scope" in provider.prompt
    assert "Do not add a standalone `Evidence` heading" in provider.prompt
    assert len(usage_tracker.reservations) == 1
    assert usage_tracker.finalized[0][1:3] == (100, 20)
    assert usage_tracker.finalized[0][-1] == "completed"
    assert answer_cache.saved == [response]
    assert response.cached is False

    cached_response = asyncio.run(service.ask(object(), REPOSITORY_ID, OWNER_ID, "Where is StudentLifeEnv defined?"))
    assert cached_response.answer == response.answer
    assert cached_response.cached is True
    assert len(usage_tracker.reservations) == 1


def test_question_skips_provider_when_no_evidence_exists() -> None:
    retrieval = FakeRetrievalService([])
    provider = FakeAnswerProvider()
    service = RepositoryQuestionService(settings(), retrieval, provider, FakeUsageTracker(), FakeAnswerCache())

    response = asyncio.run(service.ask(object(), REPOSITORY_ID, OWNER_ID, "What is missing?"))

    assert "could not find enough indexed repository evidence" in response.answer
    assert response.citations == []
    assert provider.prompt is None


def test_impact_question_includes_authoritative_traversal_context() -> None:
    retrieval = FakeRetrievalService([result("main.py", "app")])
    provider = FakeAnswerProvider()
    service = RepositoryQuestionService(
        settings(), retrieval, provider, FakeUsageTracker(), FakeAnswerCache(), FakeGraphService()
    )

    asyncio.run(service.ask(
        FakeSession([result("environment.py").chunk]), REPOSITORY_ID, OWNER_ID,
        "Analyze main.py impact.", "environment.py ", 2
    ))

    assert "Authoritative impact traversal:" in provider.prompt
    assert "Path direction: A -> B means B depends on A" in provider.prompt
    assert "A -> B means B depends on A" in provider.prompt
    assert "- Target path: environment.py" in provider.prompt
    assert "- affected_paths: server/app.py" in provider.prompt
    assert "- environment.py -> main.py -> server/app.py" in provider.prompt
    assert "only files in the supplied affected_paths are impact candidates" in provider.prompt


def test_answer_provider_error_retains_rate_limit_status() -> None:
    error = AnswerProviderError("quota reached", 429)
    assert error.status_code == 429


def test_citation_indices_keep_only_valid_referenced_evidence() -> None:
    assert RepositoryQuestionService._citation_indices("Supported by [2][1][2] and [9].", 2) == [2, 1]


def test_answer_citations_are_rebased_without_gaps() -> None:
    citations = [
        RepositoryAnswerCitation(index=1, chunk_id=uuid4(), path="one.py", start_line=1, end_line=1, title="one"),
        RepositoryAnswerCitation(index=4, chunk_id=uuid4(), path="four.py", start_line=1, end_line=1, title="four"),
    ]
    answer, rebased = RepositoryQuestionService._rebase_citations("Uses [1] and [4].", citations, [1, 4])
    assert answer == "Uses [1] and [2]."
    assert [(citation.index, citation.path) for citation in rebased] == [(1, "one.py"), (2, "four.py")]


def test_file_import_statements_are_available_to_answer_context() -> None:
    assert RepositoryQuestionService._file_import_statements({
        "file_imports": [{"statement": "import img1 from './img1.png'"}, {"source": "ignored"}]
    }) == ["import img1 from './img1.png'"]


def test_relationship_context_exposes_only_indexed_relationships() -> None:
    context = RepositoryQuestionService._relationship_context({
        "relationships": {
            "calls": [{"symbol": "run", "path": "helpers.py"}],
            "called_by": [{"symbol": "worker.py::execute", "path": "worker.py"}],
            "imports": [{"path": "helpers.py"}],
            "references": [{"symbol": "unresolved_name"}],
        }
    })

    assert "- calls: run (helpers.py)" in context
    assert "- called by: worker.py::execute (worker.py)" in context
    assert "- imports: helpers.py" in context
    assert "- references: unresolved_name" in context


def test_related_paths_include_local_imports_and_calls() -> None:
    related = result()
    related.chunk.metadata = {
        "relationships": {
            "imports": [{"path": "environment.py"}, {"path": "graders/easy.py"}],
            "calls": [{"path": "environment.py"}, {"path": "graders/medium.py"}],
        }
    }
    assert RepositoryQuestionService._related_paths([related]) == [
        "environment.py", "graders/easy.py", "graders/medium.py"
    ]
