import unittest
from types import SimpleNamespace

from app.models.meta import ColumnInfo, MetricInfo, TableInfo
from app.repositories.qdrant.metadata_repository import QdrantMetadataRepository


class FakeQdrantClient:
    def __init__(self) -> None:
        self.created_collection: dict | None = None
        self.upserted_points = []
        self.query_points_args: dict | None = None
        self.query_response_points = []

    async def collection_exists(self, collection_name: str) -> bool:
        return False

    async def create_collection(self, collection_name: str, vectors_config) -> None:
        self.created_collection = {
            "collection_name": collection_name,
            "vectors_config": vectors_config,
        }

    async def upsert(self, collection_name: str, wait: bool, points: list) -> None:
        self.upserted_points = points

    async def query_points(self, **kwargs):
        self.query_points_args = kwargs
        return SimpleNamespace(points=self.query_response_points)


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.query_text: str | None = None

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[float(index), 0.0, 0.0] for index, _ in enumerate(texts)]

    async def aembed_query(self, text: str) -> list[float]:
        self.query_text = text
        return [1.0, 0.0, 0.0]


class QdrantMetadataRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_replace_metadata_indexes_columns_and_metrics(self) -> None:
        qdrant_client = FakeQdrantClient()
        embedding_client = FakeEmbeddingClient()
        repository = QdrantMetadataRepository(qdrant_client, embedding_client)

        count = await repository.replace_metadata(
            "data_agent_meta",
            3,
            [
                TableInfo(
                    id="fact_order",
                    name="fact_order",
                    role="fact",
                    description="order fact table",
                )
            ],
            [
                ColumnInfo(
                    id="fact_order.order_amount",
                    name="order_amount",
                    type="decimal(10,2)",
                    role="measure",
                    examples=[100],
                    description="order amount",
                    alias=["GMV source"],
                    table_id="fact_order",
                )
            ],
            [
                MetricInfo(
                    id="GMV",
                    name="GMV",
                    description="gross merchandise value",
                    relevant_columns=["fact_order.order_amount"],
                    alias=["sales amount"],
                )
            ],
        )

        self.assertEqual(count, 2)
        self.assertEqual(qdrant_client.created_collection["collection_name"], "data_agent_meta")
        self.assertEqual(len(qdrant_client.upserted_points), 2)
        self.assertEqual(len(embedding_client.texts), 2)
        self.assertIn("fact_order.order_amount", embedding_client.texts[1])

        column_payload = qdrant_client.upserted_points[0].payload
        self.assertEqual(column_payload["object_type"], "column")
        self.assertEqual(column_payload["id"], "fact_order.order_amount")

        metric_payload = qdrant_client.upserted_points[1].payload
        self.assertEqual(metric_payload["object_type"], "metric")
        self.assertEqual(metric_payload["id"], "GMV")
        self.assertEqual(metric_payload["alias"], ["sales amount"])
        self.assertEqual(metric_payload["relevant_columns"], ["fact_order.order_amount"])

    async def test_search_metadata_filters_by_object_type(self) -> None:
        qdrant_client = FakeQdrantClient()
        qdrant_client.query_response_points = [
            SimpleNamespace(
                payload={"object_type": "column", "id": "fact_order.order_amount"},
                score=0.9,
            )
        ]
        embedding_client = FakeEmbeddingClient()
        repository = QdrantMetadataRepository(qdrant_client, embedding_client)

        result = await repository.search_metadata(
            collection_name="data_agent_meta",
            text="GMV",
            object_type="column",
            limit=3,
        )

        self.assertEqual(embedding_client.query_text, "GMV")
        self.assertEqual(qdrant_client.query_points_args["collection_name"], "data_agent_meta")
        self.assertEqual(qdrant_client.query_points_args["query"], [1.0, 0.0, 0.0])
        self.assertEqual(qdrant_client.query_points_args["limit"], 3)
        condition = qdrant_client.query_points_args["query_filter"].must[0]
        self.assertEqual(condition.key, "object_type")
        self.assertEqual(condition.match.value, "column")
        self.assertEqual(
            result,
            [{"object_type": "column", "id": "fact_order.order_amount", "score": 0.9}],
        )


if __name__ == "__main__":
    unittest.main()
