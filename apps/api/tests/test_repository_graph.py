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
