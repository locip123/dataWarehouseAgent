from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    query: str
    keyword: NotRequired[str]
    recalled_columns: NotRequired[list[dict[str, Any]]]
    recalled_metrics: NotRequired[list[dict[str, Any]]]
    recalled_column_values: NotRequired[list[dict[str, Any]]]
    merged_recall: NotRequired[str]
    filtered_table_info: NotRequired[dict[str, list[str]]]
    filtered_metric_info: NotRequired[list[str]]
    date_info: NotRequired[str]
    db_info: NotRequired[str]
    sql: NotRequired[str]
    sql_valid: NotRequired[bool]
    sql_error: NotRequired[str]
    sql_result: NotRequired[list[dict[str, Any]]]
