import json
from pathlib import Path

from app.agent.llm import llm
from app.agent.state import AgentState
from langgraph.runtime import Runtime


METRIC_FILTER_PROMPT = (Path(__file__).resolve().parents[3] / "prompts" / "filter_metric_info.prompt").read_text(
    encoding="utf-8"
)


def _metric_infos(merged_recall: str) -> list[str]:
    return [line for line in merged_recall.splitlines() if not ("(" in line and line.endswith(")"))]


async def filter_metric_info(
    state: AgentState, runtime: Runtime[AgentState] = Runtime()
) -> dict[str, list[str]]:
    step = "筛选指标信息"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        prompt = METRIC_FILTER_PROMPT.format(
            query=state["query"],
            metric_infos=json.dumps(_metric_infos(state["merged_recall"]), ensure_ascii=False),
        )
        response = await llm.ainvoke(prompt)
        writer({"type": "progress", "step": step, "status": "success"})
        return {"filtered_metric_info": json.loads(response.text)}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
