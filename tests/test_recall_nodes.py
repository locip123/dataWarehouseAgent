import unittest
from unittest.mock import patch

from app.agent.nodes import merge_recall, recall_column_info, recall_column_value, recall_metric_info


class FakeMetadataRepository:
    def __init__(self) -> None:
        self.calls = []

    async def search_metadata(
        self,
        collection_name: str,
        text: str,
        object_type: str,
        limit: int,
    ):
        self.calls.append(
            {
                "collection_name": collection_name,
                "text": text,
                "object_type": object_type,
                "limit": limit,
            }
        )
        return [{"object_type": object_type, "text": text, "limit": limit}]


class FakeColumnValueRepository:
    def __init__(self) -> None:
        self.calls = []

    async def search_column_values(self, index_name: str, text: str, limit: int):
        self.calls.append({"index_name": index_name, "text": text, "limit": limit})
        return [{"value": text, "limit": limit}]


class RecallNodesTest(unittest.IsolatedAsyncioTestCase):
    async def test_recall_column_info_uses_keyword(self) -> None:
        repository = FakeMetadataRepository()

        with patch.object(recall_column_info, "_metadata_repository", return_value=repository):
            result = await recall_column_info.recall_column_info({"query": "origin query", "keyword": "GMV"})

        self.assertEqual(result["recalled_columns"], [{"object_type": "column", "text": "GMV", "limit": 5}])
        self.assertEqual(repository.calls[0]["object_type"], "column")

    async def test_recall_metric_info_uses_keyword(self) -> None:
        repository = FakeMetadataRepository()

        with patch.object(recall_metric_info, "_metadata_repository", return_value=repository):
            result = await recall_metric_info.recall_metric_info({"query": "origin query", "keyword": "GMV"})

        self.assertEqual(result["recalled_metrics"], [{"object_type": "metric", "text": "GMV", "limit": 5}])
        self.assertEqual(repository.calls[0]["object_type"], "metric")

    async def test_recall_column_value_falls_back_to_query(self) -> None:
        repository = FakeColumnValueRepository()

        with patch.object(recall_column_value, "_column_value_repository", return_value=repository):
            result = await recall_column_value.recall_column_value({"query": "Beijing sales"})

        self.assertEqual(result["recalled_column_values"], [{"value": "Beijing sales", "limit": 10}])

    def test_merge_recall_info_formats_tables_and_metrics(self) -> None:
        result = merge_recall.merge_recall_info(
            {
                "query": "GMV",
                "recalled_columns": [
                    {"table_id": "fact_order", "name": "amount"},
                    {"id": "dim_city.city_name"},
                    {"table_id": "fact_order", "name": "amount"},
                ],
                "recalled_metrics": [{"name": "GMV"}, {"id": "order_count"}],
                "recalled_column_values": [
                    {"table_id": "fact_order", "column_name": "city_id", "value": "Beijing"},
                    {"column_id": "dim_city.city_name", "value": "Beijing"},
                ],
            }
        )

        self.assertEqual(
            result["merged_recall"],
            "fact_order(amount,city_id)\ndim_city(city_name)\nGMV\norder_count",
        )


if __name__ == "__main__":
    unittest.main()
