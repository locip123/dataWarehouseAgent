from typing import cast

import jieba.analyse

from app.agent.state import AgentState
from langgraph.runtime import Runtime


def extract_keyword(state: AgentState, runtime: Runtime[AgentState] = Runtime()) -> dict[str, str]:
    step = "抽取关键词"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        query = state["query"]
        keywords = cast(list[str], jieba.analyse.extract_tags(query, withWeight=False, withFlag=False))
        keyword = " ".join(keywords)
        writer({"type": "progress", "step": step, "status": "success"})
        return {"keyword": keyword or query}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
