import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.agent.nodes import context


class ContextTest(unittest.IsolatedAsyncioTestCase):
    def test_date_info_includes_date_weekday_and_quarter(self) -> None:
        self.assertEqual(
            context._date_info(datetime(2026, 7, 12)),
            "当前日期：2026-07-12\n星期：星期日\n季度：第3季度",
        )

    async def test_add_context_includes_database_metadata(self) -> None:
        with patch.object(context, "_database_version", new=AsyncMock(return_value="8.0.36")):
            result = await context.add_context({"query": "北京订单销售额"})

        self.assertIn("数据库类型：MySQL", result["db_info"])
        self.assertIn("数据库版本：8.0.36", result["db_info"])
        self.assertIn("数据库名称：dw", result["db_info"])


if __name__ == "__main__":
    unittest.main()
