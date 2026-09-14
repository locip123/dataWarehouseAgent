import unittest
from unittest.mock import patch

from app.agent.nodes import filter_metric_info


class FakeResponse:
    text = '["GMV"]'


class FakeLLM:
    def __init__(self) -> None:
        self.prompts = []

    async def ainvoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse()


class FilterMetricInfoTest(unittest.IsolatedAsyncioTestCase):
    async def test_filter_metric_info_uses_merged_metric_recall(self) -> None:
        fake_llm = FakeLLM()

        with patch.object(filter_metric_info, "llm", fake_llm):
            result = await filter_metric_info.filter_metric_info(
                {
                    "query": "北京订单销售额",
                    "merged_recall": "fact_order(amount,city_id)\ndim_city(city_name)\nGMV\norder_count",
                }
            )

        self.assertEqual(result, {"filtered_metric_info": ["GMV"]})
        self.assertIn("北京订单销售额", fake_llm.prompts[0])
        self.assertIn('["GMV", "order_count"]', fake_llm.prompts[0])
        self.assertNotIn("fact_order(amount,city_id)", fake_llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
