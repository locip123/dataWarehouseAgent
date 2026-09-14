from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.models.meta import ColumnInfo, MetricInfo, TableInfo


class QdrantMetadataRepository:
    def __init__(
        self,
        client: AsyncQdrantClient,
        embedding_client: Any,
    ):
        self.client = client
        self.embedding_client = embedding_client

    async def replace_metadata(
        self,
        collection_name: str,
        embedding_size: int,
        tables: list[TableInfo],
        columns: list[ColumnInfo],
        metrics: list[MetricInfo],
    ) -> int:
        await self._recreate_collection(collection_name, embedding_size)
        if not columns and not metrics:
            return 0

        table_by_id = {table.id: table for table in tables}
        texts = [
            self._build_embedding_text(table_by_id.get(column.table_id), column)
            for column in columns
        ] + [self._build_metric_embedding_text(metric) for metric in metrics]
        vectors = await self.embedding_client.aembed_documents(texts)
        points = [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, column.id)),
                vector=vector,
                payload=self._column_payload(column),
            )
            for column, vector in zip(columns, vectors[: len(columns)], strict=True)
        ] + [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"metric:{metric.id}")),
                vector=vector,
                payload=self._metric_payload(metric),
            )
            for metric, vector in zip(metrics, vectors[len(columns):], strict=True)
        ]

        await self.client.upsert(
            collection_name=collection_name,
            wait=True,
            points=points,
        )
        return len(points)

    async def search_metadata(
        self,
        collection_name: str,
        text: str,
        object_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if not text:
            return []

        vector = await self.embedding_client.aembed_query(text)
        response = await self.client.query_points(
            collection_name=collection_name,
            query=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="object_type",
                        match=MatchValue(value=object_type),
                    )
                ]
            ),
            with_payload=True,
            limit=limit,
        )
        return [self._point_to_dict(point) for point in response.points]

    async def _recreate_collection(
        self,
        collection_name: str,
        embedding_size: int,
    ) -> None:
        if await self.client.collection_exists(collection_name=collection_name):
            await self.client.delete_collection(collection_name=collection_name)

        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
        )

    @staticmethod
    def _build_embedding_text(
        table: TableInfo | None,
        column: ColumnInfo,
    ) -> str:
        parts = [
            table.name if table is not None else column.table_id,
            table.description if table is not None else None,
            column.name,
            column.description,
            *QdrantMetadataRepository._list_text(column.alias),
        ]
        return "\n".join(str(part) for part in parts if part not in (None, ""))

    @staticmethod
    def _list_text(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        if value in (None, ""):
            return []
        return [str(value)]

    @staticmethod
    def _build_metric_embedding_text(metric: MetricInfo) -> str:
        parts = [
            metric.name,
            metric.description,
            *QdrantMetadataRepository._list_text(metric.alias),
            *QdrantMetadataRepository._list_text(metric.relevant_columns),
        ]
        return "\n".join(str(part) for part in parts if part not in (None, ""))

    @staticmethod
    def _column_payload(column: ColumnInfo) -> dict[str, Any]:
        return {
            "object_type": "column",
            "id": column.id,
            "name": column.name,
            "type": column.type,
            "role": column.role,
            "examples": column.examples,
            "description": column.description,
            "alias": column.alias,
            "table_id": column.table_id,
        }

    @staticmethod
    def _metric_payload(metric: MetricInfo) -> dict[str, Any]:
        return {
            "object_type": "metric",
            "id": metric.id,
            "name": metric.name,
            "description": metric.description,
            "alias": metric.alias,
            "relevant_columns": metric.relevant_columns,
        }

    @staticmethod
    def _point_to_dict(point: ScoredPoint) -> dict[str, Any]:
        payload = dict(point.payload or {})
        payload["score"] = point.score
        return payload
