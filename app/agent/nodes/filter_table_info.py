import json
from pathlib import Path

from app.agent.llm import llm
from app.agent.state import AgentState
from langgraph.runtime import Runtime


TABLE_FILTER_PROMPT = (Path(__file__).resolve().parents[3] / "prompts" / "filter_table_info.prompt").read_text(
    encoding="utf-8"
)


def _table_infos(merged_recall: str) -> str:
    return "\n".join(line for line in merged_recall.splitlines() if "(" in line and line.endswith(")"))


async def filter_table_info(
    state: AgentState, runtime: Runtime[AgentState] = Runtime()
) -> dict[str, dict[str, list[str]]]:
    step = "筛选表信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        prompt = TABLE_FILTER_PROMPT.format(
            query=state["query"],
            table_infos=_table_infos(state["merged_recall"]),
        )
        response = await llm.ainvoke(prompt)
        writer({"type": "progress", "step": step, "status": "success"})
        return {"filtered_table_info": json.loads(response.text)}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
