from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_version(self) -> str:
        result = await self.session.execute(text("SELECT VERSION()"))
        return str(result.scalar_one())

    async def explain(self, sql: str) -> None:
        await self.session.execute(text(f"EXPLAIN {sql}"))

    async def execute(self, sql: str) -> list[dict[str, Any]]:
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings()]
