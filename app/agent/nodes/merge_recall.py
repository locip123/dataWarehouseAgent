from typing import Any

from app.agent.state import AgentState
from langgraph.runtime import Runtime


def merge_recall_info(state: AgentState, runtime: Runtime[AgentState] = Runtime()) -> dict[str, str]:
    step = "合并召回信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        tables: dict[str, list[str]] = {}
        metrics: list[str] = []

        for column in state.get("recalled_columns", []):
            _add_table_column(tables, _table_id(column, "id"), _column_name(column, "name", "id"))

        for column_value in state.get("recalled_column_values", []):
            _add_table_column(
                tables,
                _table_id(column_value, "column_id"),
                _column_name(column_value, "column_name", "column_id"),
            )

        for metric in state.get("recalled_metrics", []):
            metric_name = metric.get("name") or metric.get("id")
            if metric_name not in (None, ""):
                metrics.append(str(metric_name))

        lines = [f"{table}({','.join(columns)})" for table, columns in tables.items()]
        lines.extend(metrics)
        writer({"type": "progress", "step": step, "status": "success"})
        return {"merged_recall": "\n".join(lines)}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise


def _add_table_column(tables: dict[str, list[str]], table_id: str | None, column_name: str | None) -> None:
    if table_id is None or column_name is None:
        return

    columns = tables.setdefault(table_id, [])
    if column_name not in columns:
        columns.append(column_name)


def _table_id(item: dict[str, Any], id_key: str) -> str | None:
    table_id = item.get("table_id")
    if table_id not in (None, ""):
        return str(table_id)

    object_id = item.get(id_key)
    if not isinstance(object_id, str) or "." not in object_id:
        return None
    return object_id.rsplit(".", 1)[0]


def _column_name(item: dict[str, Any], name_key: str, id_key: str) -> str | None:
    name = item.get(name_key)
    if name not in (None, ""):
        return str(name)

    object_id = item.get(id_key)
    if not isinstance(object_id, str) or "." not in object_id:
        return None
    return object_id.rsplit(".", 1)[1]
