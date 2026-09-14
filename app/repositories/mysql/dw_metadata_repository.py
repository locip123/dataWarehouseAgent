from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMetadataRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(
        self,
        schema: str,
        table_names: Sequence[str],
    ) -> dict[str, dict[str, str]]:
        if not table_names:
            return {}

        stmt = text(
            """
            SELECT
                TABLE_NAME AS table_name,
                COLUMN_NAME AS column_name,
                COLUMN_TYPE AS column_type
            FROM information_schema.columns
            WHERE TABLE_SCHEMA = :schema
              AND TABLE_NAME IN :table_names
            """
        ).bindparams(bindparam("table_names", expanding=True))

        result = await self.session.execute(
            stmt,
            {"schema": schema, "table_names": list(dict.fromkeys(table_names))},
        )

        column_types: dict[str, dict[str, str]] = {}
        for row in result.mappings():
            table_name = row["table_name"]
            column_name = row["column_name"]
            column_type = row["column_type"]
            column_types.setdefault(table_name, {})[column_name] = column_type

        return column_types

    async def get_column_examples(
        self,
        schema: str,
        columns_by_table: Mapping[str, Sequence[str]],
        limit: int = 3,
    ) -> dict[str, dict[str, list[Any]]]:
        examples: dict[str, dict[str, list[Any]]] = {}
        schema_name = self._quote_identifier(schema)

        for table_name, column_names in columns_by_table.items():
            table_examples: dict[str, list[Any]] = {}
            table_identifier = f"{schema_name}.{self._quote_identifier(table_name)}"

            for column_name in dict.fromkeys(column_names):
                column_identifier = self._quote_identifier(column_name)
                stmt = text(
                    f"""
                    SELECT DISTINCT {column_identifier} AS example
                    FROM {table_identifier}
                    WHERE {column_identifier} IS NOT NULL
                    LIMIT :limit
                    """
                )
                result = await self.session.execute(stmt, {"limit": limit})
                table_examples[column_name] = [
                    row["example"] for row in result.mappings()
                ]

            examples[table_name] = table_examples

        return examples

    async def get_distinct_column_values(
        self,
        schema: str,
        columns_by_table: Mapping[str, Sequence[str]],
    ) -> dict[str, dict[str, list[Any]]]:
        values: dict[str, dict[str, list[Any]]] = {}
        schema_name = self._quote_identifier(schema)

        for table_name, column_names in columns_by_table.items():
            table_values: dict[str, list[Any]] = {}
            table_identifier = f"{schema_name}.{self._quote_identifier(table_name)}"

            for column_name in dict.fromkeys(column_names):
                column_identifier = self._quote_identifier(column_name)
                stmt = text(
                    f"""
                    SELECT DISTINCT {column_identifier} AS value
                    FROM {table_identifier}
                    WHERE {column_identifier} IS NOT NULL
                    ORDER BY {column_identifier}
                    """
                )
                result = await self.session.execute(stmt)
                table_values[column_name] = [
                    row["value"] for row in result.mappings()
                ]

            values[table_name] = table_values

        return values

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return f"`{identifier.replace('`', '``')}`"
