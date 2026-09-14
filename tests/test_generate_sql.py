import unittest
from unittest.mock import patch

from app.agent.nodes import generate_sql


class FakeResponse:
    text = "  SELECT SUM(amount) AS gmv FROM fact_order WHERE city_id = 1  "


class FakeLLM:
    def __init__(self) -> None:
        self.prompts = []

    async def ainvoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse()


class GenerateSQLTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_sql_combines_all_context(self) -> None:
        fake_llm = FakeLLM()

        with patch.object(generate_sql, "llm", fake_llm):
            result = await generate_sql.generate_sql(
                {
                    "query": "北京订单销售额",
                    "filtered_table_info": {"fact_order": ["amount", "city_id"]},
                    "filtered_metric_info": ["GMV"],
                    "date_info": "当前日期：2026-07-12\n星期：星期日\n季度：第3季度",
                    "db_info": "数据库类型：MySQL\n数据库版本：8.0.36\n数据库名称：dw",
                }
            )

        self.assertEqual(result, {"sql": "SELECT SUM(amount) AS gmv FROM fact_order WHERE city_id = 1"})
        self.assertIn("北京订单销售额", fake_llm.prompts[0])
        self.assertIn('{"fact_order": ["amount", "city_id"]}', fake_llm.prompts[0])
        self.assertIn('["GMV"]', fake_llm.prompts[0])
        self.assertIn("当前日期：2026-07-12", fake_llm.prompts[0])
        self.assertIn("数据库版本：8.0.36", fake_llm.prompts[0])


if __name__ == "__main__":
    unittest.main()
