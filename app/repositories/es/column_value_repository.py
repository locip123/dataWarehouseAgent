from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha1
from typing import Any

from elasticsearch import AsyncElasticsearch

from app.models.meta import ColumnInfo

COLUMN_VALUE_DOC_TYPE = "column_value"


class ESColumnValueRepository:
    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def replace_column_values(
        self,
        index_name: str,
        columns: list[ColumnInfo],
        values_by_table: Mapping[str, Mapping[str, list[Any]]],
    ) -> int:
        await self._ensure_index(index_name)
        await self._delete_existing_column_values(index_name)

        operations: list[dict[str, Any]] = []
        column_by_id = {column.id: column for column in columns}

        for table_name, table_values in values_by_table.items():
            for column_name, values in table_values.items():
                column_id = f"{table_name}.{column_name}"
                column = column_by_id.get(column_id)
                if column is None:
                    continue

                for value in values:
                    document = self._build_document(column, value)
                    operations.append({"index": {"_index": index_name, "_id": document["id"]}})
                    operations.append(document)

        if not operations:
            return 0

        response = await self.client.bulk(operations=operations, refresh=True)
        if response.get("errors"):
            raise RuntimeError(f"ES 字段值同步失败: {response}")

        return len(operations) // 2

    async def search_column_values(
        self,
        index_name: str,
        text: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not text:
            return []

        response = await self.client.search(
            index=index_name,
            query={
                "bool": {
                    "filter": [{"term": {"doc_type": COLUMN_VALUE_DOC_TYPE}}],
                    "must": [
                        {
                            "multi_match": {
                                "query": text,
                                "fields": [
                                    "value",
                                    "column_name",
                                    "column_alias",
                                    "column_description",
                                ],
                            }
                        }
                    ],
                }
            },
            size=limit,
        )
        return [self._hit_to_dict(hit) for hit in response["hits"]["hits"]]

    async def _ensure_index(self, index_name: str) -> None:
        if await self.client.indices.exists(index=index_name):
            return

        await self.client.indices.create(
            index=index_name,
            mappings={
                "properties": {
                    "doc_type": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "table_id": {"type": "keyword"},
                    "column_id": {"type": "keyword"},
                    "column_name": {"type": "keyword"},
                    "column_alias": {"type": "keyword"},
                    "value": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "value_type": {"type": "keyword"},
                }
            },
        )

    async def _delete_existing_column_values(self, index_name: str) -> None:
        await self.client.delete_by_query(
            index=index_name,
            query={"term": {"doc_type": COLUMN_VALUE_DOC_TYPE}},
            conflicts="proceed",
            refresh=True,
        )

    def _build_document(self, column: ColumnInfo, value: Any) -> dict[str, Any]:
        value_text = self._value_text(value)
        document_id = sha1(f"{column.id}:{value_text}".encode("utf-8")).hexdigest()

        return {
            "doc_type": COLUMN_VALUE_DOC_TYPE,
            "id": document_id,
            "table_id": column.table_id,
            "column_id": column.id,
            "column_name": column.name,
            "column_alias": column.alias,
            "column_description": column.description,
            "value": value_text,
            "value_raw": self._json_value(value),
            "value_type": type(value).__name__,
        }

    @staticmethod
    def _value_text(value: Any) -> str:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _hit_to_dict(hit: dict[str, Any]) -> dict[str, Any]:
        source = dict(hit.get("_source") or {})
        source["score"] = hit.get("_score")
        return source
