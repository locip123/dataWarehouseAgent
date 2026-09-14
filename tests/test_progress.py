import unittest
from unittest.mock import AsyncMock, patch

from langgraph.runtime import Runtime
from sqlalchemy.exc import SQLAlchemyError

from app.agent.nodes import keyword, sql_validate


class ProgressTest(unittest.IsolatedAsyncioTestCase):
    def test_extract_keyword_emits_running_and_success(self) -> None:
        events: list[dict[str, str]] = []

        keyword.extract_keyword(
            {"query": "北京订单销售额"},
            Runtime(stream_writer=events.append),
        )

        self.assertEqual([event["status"] for event in events], ["running", "success"])

    def test_extract_keyword_emits_error_and_reraises(self) -> None:
        events: list[dict[str, str]] = []

        with patch.object(keyword.jieba.analyse, "extract_tags", side_effect=RuntimeError("boom")):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                keyword.extract_keyword(
                    {"query": "北京订单销售额"},
                    Runtime(stream_writer=events.append),
                )

        self.assertEqual([event["status"] for event in events], ["running", "error"])

    async def test_validate_sql_emits_error_for_correctable_database_error(self) -> None:
        events: list[dict[str, str]] = []

        with patch.object(
            sql_validate,
            "_explain_sql",
            new=AsyncMock(side_effect=SQLAlchemyError("Unknown column 'amounts'")),
        ):
            result = await sql_validate.validate_sql(
                {"query": "订单数", "sql": "SELECT amounts FROM fact_order"},
                Runtime(stream_writer=events.append),
            )

        self.assertEqual(result["sql_valid"], False)
        self.assertEqual([event["status"] for event in events], ["running", "error"])


if __name__ == "__main__":
    unittest.main()
