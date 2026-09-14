import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import SQLAlchemyError

from app.agent.nodes import sql_validate


class SQLValidateTest(unittest.IsolatedAsyncioTestCase):
    async def test_validate_sql_routes_valid_statement_to_execution(self) -> None:
        with patch.object(sql_validate, "_explain_sql", new=AsyncMock()):
            result = await sql_validate.validate_sql({"query": "订单数", "sql": "SELECT COUNT(*) FROM fact_order"})

        self.assertEqual(result, {"sql_valid": True, "sql_error": ""})
        self.assertEqual(sql_validate.route_sql_validation(result), "execute_sql")

    async def test_validate_sql_routes_database_error_to_correction(self) -> None:
        error = SQLAlchemyError("Unknown column 'amounts'")

        with patch.object(sql_validate, "_explain_sql", new=AsyncMock(side_effect=error)):
            result = await sql_validate.validate_sql({"query": "订单数", "sql": "SELECT amounts FROM fact_order"})

        self.assertEqual(result, {"sql_valid": False, "sql_error": "Unknown column 'amounts'"})
        self.assertEqual(sql_validate.route_sql_validation(result), "correct_sql")

    async def test_execute_sql_returns_query_rows(self) -> None:
        with patch.object(sql_validate, "_execute_sql", new=AsyncMock(return_value=[{"order_count": 12}])):
            result = await sql_validate.execute_sql({"query": "订单数", "sql": "SELECT COUNT(*) AS order_count FROM fact_order"})

        self.assertEqual(result, {"sql_result": [{"order_count": 12}]})


if __name__ == "__main__":
    unittest.main()
