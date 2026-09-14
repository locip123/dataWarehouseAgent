import unittest

from app.repositories.es.column_value_repository import (
    COLUMN_VALUE_DOC_TYPE,
    ESColumnValueRepository,
)


class FakeESClient:
    def __init__(self) -> None:
        self.search_args: dict | None = None

    async def search(self, **kwargs):
        self.search_args = kwargs
        return {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "doc_type": COLUMN_VALUE_DOC_TYPE,
                            "column_id": "dim_city.city_name",
                            "value": "北京",
                        },
                        "_score": 1.5,
                    }
                ]
            }
        }


class ESColumnValueRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_search_column_values_filters_and_matches_value_fields(self) -> None:
        client = FakeESClient()
        repository = ESColumnValueRepository(client)

        result = await repository.search_column_values(
            index_name="data_agent",
            text="北京",
            limit=7,
        )

        self.assertEqual(client.search_args["index"], "data_agent")
        self.assertEqual(client.search_args["size"], 7)
        query = client.search_args["query"]["bool"]
        self.assertEqual(query["filter"], [{"term": {"doc_type": COLUMN_VALUE_DOC_TYPE}}])
        self.assertEqual(query["must"][0]["multi_match"]["query"], "北京")
        self.assertEqual(
            query["must"][0]["multi_match"]["fields"],
            ["value", "column_name", "column_alias", "column_description"],
        )
        self.assertEqual(
            result,
            [
                {
                    "doc_type": COLUMN_VALUE_DOC_TYPE,
                    "column_id": "dim_city.city_name",
                    "value": "北京",
                    "score": 1.5,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
