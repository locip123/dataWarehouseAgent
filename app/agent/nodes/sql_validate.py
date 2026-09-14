from typing import Any, Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from langgraph.runtime import Runtime

from app.agent.state import AgentState
from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.repositories import SQLRepository


def _dw_engine() -> AsyncEngine:
    if dw_mysql_client_manager.engine is None:
        dw_mysql_client_manager.init()
    assert dw_mysql_client_manager.engine is not None
    return dw_mysql_client_manager.engine


async def _explain_sql(sql: str) -> None:
    async with AsyncSession(_dw_engine()) as session:
        await SQLRepository(session).explain(sql)


async def _execute_sql(sql: str) -> list[dict[str, Any]]:
    async with AsyncSession(_dw_engine()) as session:
        return await SQLRepository(session).execute(sql)


async def validate_sql(state: AgentState, runtime: Runtime[AgentState] = Runtime()) -> dict[str, bool | str]:
    step = "验证SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        await _explain_sql(state["sql"])
    except SQLAlchemyError as error:
        writer({"type": "progress", "step": step, "status": "error"})
        return {"sql_valid": False, "sql_error": str(error)}
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
    writer({"type": "progress", "step": step, "status": "success"})
    return {"sql_valid": True, "sql_error": ""}


def route_sql_validation(state: AgentState) -> Literal["execute_sql", "correct_sql"]:
    return "execute_sql" if state["sql_valid"] else "correct_sql"


async def execute_sql(
    state: AgentState, runtime: Runtime[AgentState] = Runtime()
) -> dict[str, list[dict[str, Any]]]:
    step = "执行SQL"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})
    try:
        result = {"sql_result": await _execute_sql(state["sql"])}
        writer({"type": "progress", "step": step, "status": "success"})
        return result
    except Exception:
        writer({"type": "progress", "step": step, "status": "error"})
        raise
