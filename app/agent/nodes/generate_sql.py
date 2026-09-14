import json
from pathlib import Path

from app.agent.llm import llm
from app.agent.state import AgentState
from langgraph.runtime import Runtime


SQL_GENERATION_PROMPT = (Path(__file__).resolve().parents[3] / "prompts" / "generate_sql.prompt").read_text(
    encoding="utf-8"
)


async def generate_sql(state: AgentState, runtime: Runtime[AgentState] = Runtime()) -> dict[str, str]:
    step = "生成SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        prompt = SQL_GENERATION_PROMPT.format(
            query=state["query"],
            table_infos=json.dumps(state["filtered_table_info"], ensure_ascii=False),
            metric_infos=json.dumps(state["filtered_metric_info"], ensure_ascii=False),
            date_info=state["date_info"],
            db_info=state["db_info"],
        )
        response = await llm.ainvoke(prompt)
        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": response.text.strip()}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
