import unittest
from unittest.mock import patch

from app.agent.nodes import filter_table_info


class FakeResponse:
    text = '{"fact_order": ["amount", "city_id"]}'


class FakeLLM:
    def __init__(self) -> None:
        self.prompts = []

    async def ainvoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse()


class FilterTableInfoTest(unittest.IsolatedAsyncioTestCase):
    async def test_filter_table_info_uses_merged_table_recall(self) -> None:
        fake_llm = FakeLLM()

        with patch.object(filter_table_info, "llm", fake_llm):
            result = await filter_table_info.filter_table_info(
                {
                    "query": "北京订单销售额",
                    "merged_recall": "fact_order(amount,city_id)\ndim_city(city_name)\nGMV",
                }
            )

        self.assertEqual(result, {"filtered_table_info": {"fact_order": ["amount", "city_id"]}})
        self.assertIn("北京订单销售额", fake_llm.prompts[0])
        self.assertIn("fact_order(amount,city_id)", fake_llm.prompts[0])
        self.assertIn("dim_city(city_name)", fake_llm.prompts[0])
        self.assertNotIn("GMV", fake_llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
