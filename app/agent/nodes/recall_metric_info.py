from typing import Any

from app.agent.state import AgentState
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.conf.app_config import app_config
from app.repositories.qdrant import QdrantMetadataRepository
from langgraph.runtime import Runtime

METRIC_RECALL_LIMIT = 5


def _recall_text(state: AgentState) -> str:
    return state.get("keyword") or state["query"]


def _metadata_repository() -> QdrantMetadataRepository:
    if qdrant_client_manager.client is None:
        qdrant_client_manager.init()
    if embedding_client_manager.client is None:
        embedding_client_manager.init()

    return QdrantMetadataRepository(
        qdrant_client_manager.client,
        embedding_client_manager.client,
    )


async def recall_metric_info(
    state: AgentState, runtime: Runtime[AgentState] = Runtime()
) -> dict[str, list[dict[str, Any]]]:
    step = "召回指标信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        repository = _metadata_repository()
        recalled_metrics = await repository.search_metadata(
            collection_name=app_config.qdrant.collection_name,
            text=_recall_text(state),
            object_type="metric",
            limit=METRIC_RECALL_LIMIT,
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"recalled_metrics": recalled_metrics}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
