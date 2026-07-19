from app.modules.graph.service import RepositoryGraphService


def get_repository_graph_service() -> RepositoryGraphService:
    return RepositoryGraphService()
