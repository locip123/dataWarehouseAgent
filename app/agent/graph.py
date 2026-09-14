from langgraph.graph import END, START, StateGraph

from app.agent.nodes.context import add_context
from app.agent.nodes.filter_table_info import filter_table_info
from app.agent.nodes.filter_metric_info import filter_metric_info
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.keyword import extract_keyword
from app.agent.nodes.merge_recall import merge_recall_info
from app.agent.nodes.recall_column_info import recall_column_info
from app.agent.nodes.recall_column_value import recall_column_value
from app.agent.nodes.recall_metric_info import recall_metric_info
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.sql_validate import execute_sql, route_sql_validation, validate_sql
from app.agent.state import AgentState


workflow = StateGraph(AgentState)
workflow.add_node("add_context", add_context)
workflow.add_node("extract_keyword", extract_keyword)
workflow.add_node("recall_column_info", recall_column_info)
workflow.add_node("recall_metric_info", recall_metric_info)
workflow.add_node("recall_column_value", recall_column_value)
workflow.add_node("merge_recall_info", merge_recall_info)
workflow.add_node("filter_table_info", filter_table_info)
workflow.add_node("filter_metric_info", filter_metric_info)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("validate_sql", validate_sql)
workflow.add_node("correct_sql", correct_sql)
workflow.add_node("execute_sql", execute_sql)

workflow.add_edge(START, "add_context")
workflow.add_edge(START, "extract_keyword")
workflow.add_edge("extract_keyword", "recall_column_info")
workflow.add_edge("extract_keyword", "recall_metric_info")
workflow.add_edge("extract_keyword", "recall_column_value")
workflow.add_edge("recall_column_info", "merge_recall_info")
workflow.add_edge("recall_metric_info", "merge_recall_info")
workflow.add_edge("recall_column_value", "merge_recall_info")
workflow.add_edge("merge_recall_info", "filter_table_info")
workflow.add_edge("merge_recall_info", "filter_metric_info")
workflow.add_edge(["add_context", "filter_table_info", "filter_metric_info"], "generate_sql")
workflow.add_edge("generate_sql", "validate_sql")
workflow.add_conditional_edges("validate_sql", route_sql_validation)
workflow.add_edge("correct_sql", "validate_sql")
workflow.add_edge("execute_sql", END)

graph = workflow.compile()
