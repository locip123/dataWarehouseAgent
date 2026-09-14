from typing import Any

from app.agent.state import AgentState
from app.clients.es_client_manager import es_client_manager
from app.conf.app_config import app_config
from app.repositories.es import ESColumnValueRepository
from langgraph.runtime import Runtime

COLUMN_VALUE_RECALL_LIMIT = 10


def _recall_text(state: AgentState) -> str:
    return state.get("keyword") or state["query"]


def _column_value_repository() -> ESColumnValueRepository:
    if es_client_manager.client is None:
        es_client_manager.init()

    return ESColumnValueRepository(es_client_manager.client)


async def recall_column_value(
    state: AgentState, runtime: Runtime[AgentState] = Runtime()
) -> dict[str, list[dict[str, Any]]]:
    step = "召回字段值"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        repository = _column_value_repository()
        recalled_column_values = await repository.search_column_values(
            index_name=app_config.es.index_name,
            text=_recall_text(state),
            limit=COLUMN_VALUE_RECALL_LIMIT,
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"recalled_column_values": recalled_column_values}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
