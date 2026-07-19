from types import SimpleNamespace

from app.modules.graph.service import RepositoryGraphService


def edge(**values):
    defaults = {
        "relationship_type": "calls",
        "source_path": "app.py",
        "target_path": "environment.py",
        "target_stable_symbol_id": "environment.py::StudentLifeEnv",
        "target_symbol": "StudentLifeEnv",
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_impact_deduplicates_file_imports_but_keeps_distinct_symbol_calls() -> None:
    rows = [
        edge(relationship_type="imports", source_path="runner.py", target_symbol="environment"),
        edge(relationship_type="imports", source_path="runner.py", target_symbol="StudentLifeEnv"),
        edge(relationship_type="calls", source_path="runner.py", target_symbol="env.reset"),
        edge(relationship_type="calls", source_path="runner.py", target_symbol="env.step"),
    ]
    deduplicated = RepositoryGraphService._deduplicate(rows)
    assert [row.target_symbol for row in deduplicated] == ["environment", "env.reset", "env.step"]


def test_impact_test_path_detection() -> None:
    assert RepositoryGraphService._is_test_path("test_environment.py")
    assert RepositoryGraphService._is_test_path("tests/test_environment.py")
    assert not RepositoryGraphService._is_test_path("environment.py")


def test_impact_path_normalization_removes_accidental_query_whitespace() -> None:
    assert RepositoryGraphService._normalize_path(" environment.py \t") == "environment.py"


def test_symbol_impact_follows_only_resolved_stable_symbol_edges() -> None:
    rows = [
        edge(
            source_path="main.py",
            source_stable_symbol_id="main.py::step_all",
            target_stable_symbol_id="environment.py::StudentLifeEnv::step",
        ),
        edge(
            source_path="server/app.py",
            source_stable_symbol_id="server/app.py::main",
            target_stable_symbol_id="main.py::step_all",
        ),
        edge(
            source_path="test_main.py",
            source_stable_symbol_id="test_main.py::test_step",
            target_stable_symbol_id="main.py::step_all",
        ),
        edge(
            relationship_type="imports",
            source_path="unrelated.py",
            source_stable_symbol_id="unrelated.py::helper",
            target_stable_symbol_id="environment.py::StudentLifeEnv::step",
        ),
    ]
    paths, affected = RepositoryGraphService._symbol_reverse_paths(
        rows, "environment.py::StudentLifeEnv::step", depth=2
    )
    assert paths == [
        ["environment.py::StudentLifeEnv::step", "main.py::step_all"],
        ["environment.py::StudentLifeEnv::step", "main.py::step_all", "server/app.py::main"],
    ]
    assert affected == {"main.py::step_all", "server/app.py::main"}
