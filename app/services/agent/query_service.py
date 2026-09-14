from collections.abc import AsyncIterator
from typing import Any

from app.agent.graph import graph
from app.core.log import logger


async def stream_query(query: str) -> AsyncIterator[dict[str, Any]]:
    try:
        async for mode, data in graph.astream(
            {"query": query},
            stream_mode=["custom", "updates"],
        ):
            if mode == "custom":
                yield data
            elif mode == "updates":
                for update in data.values():
                    if "sql_result" in update:
                        yield {"type": "result", "data": update["sql_result"]}
    except Exception as error:
        logger.exception("数据查询失败")
        yield {"type": "error", "message": str(error) or "查询失败"}
