from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta import ColumnInfo, ColumnMetric, MetricInfo, TableInfo


class MetaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def replace_all(
        self,
        tables: Sequence[TableInfo],
        columns: Sequence[ColumnInfo],
        metrics: Sequence[MetricInfo],
        column_metrics: Sequence[ColumnMetric],
    ) -> None:
        await self.session.execute(delete(ColumnMetric))
        await self.session.execute(delete(MetricInfo))
        await self.session.execute(delete(ColumnInfo))
        await self.session.execute(delete(TableInfo))

        self.session.add_all([*tables, *columns, *metrics, *column_metrics])
