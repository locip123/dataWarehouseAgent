from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.runtime import Runtime

from app.agent.state import AgentState
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.repositories import SQLRepository


WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def _date_info(now: datetime) -> str:
    quarter = (now.month - 1) // 3 + 1
    return f"当前日期：{now:%Y-%m-%d}\n星期：{WEEKDAYS[now.weekday()]}\n季度：第{quarter}季度"


async def _database_version() -> str:
    if dw_mysql_client_manager.engine is None:
        dw_mysql_client_manager.init()

    try:
        async with AsyncSession(dw_mysql_client_manager.engine) as session:
            return await SQLRepository(session).get_version()
    except SQLAlchemyError:
        return "未知"


async def add_context(state: AgentState, runtime: Runtime[AgentState] = Runtime()) -> dict[str, str]:
    step = "补充上下文"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        version = await _database_version()
        db_info = "\n".join(
            (
                "数据库类型：MySQL",
                f"数据库版本：{version}",
                f"数据库名称：{dw_mysql_client_manager.config.database}",
            )
        )
        writer({"type": "progress", "step": step, "status": "success"})
        return {"date_info": _date_info(datetime.now()), "db_info": db_info}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
