import unittest
from unittest.mock import patch

from app.agent.nodes import correct_sql


class FakeResponse:
    text = "  SELECT amount FROM fact_order  "


class FakeLLM:
    def __init__(self) -> None:
        self.prompts = []

    async def ainvoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse()


class CorrectSQLTest(unittest.IsolatedAsyncioTestCase):
    async def test_correct_sql_uses_error_and_all_context(self) -> None:
        fake_llm = FakeLLM()

        with patch.object(correct_sql, "llm", fake_llm):
            result = await correct_sql.correct_sql(
                {
                    "query": "北京订单销售额",
                    "filtered_table_info": {"fact_order": ["amount", "city_id"]},
                    "filtered_metric_info": ["GMV"],
                    "date_info": "当前日期：2026-07-12",
                    "db_info": "数据库类型：MySQL\n数据库版本：8.0.36",
                    "sql": "SELECT amounts FROM fact_order",
                    "sql_error": "Unknown column 'amounts'",
                }
            )

        self.assertEqual(result, {"sql": "SELECT amount FROM fact_order"})
        self.assertIn("SELECT amounts FROM fact_order", fake_llm.prompts[0])
        self.assertIn("Unknown column 'amounts'", fake_llm.prompts[0])
        self.assertIn('{"fact_order": ["amount", "city_id"]}', fake_llm.prompts[0])
        self.assertIn('["GMV"]', fake_llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
