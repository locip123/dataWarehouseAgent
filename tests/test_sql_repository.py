import unittest

from app.repositories.mysql.sql_repository import SQLRepository


class FakeResult:
    def __init__(self, version: str = "8.0.36", rows: list[dict] | None = None) -> None:
        self.version = version
        self.rows = rows or []

    def scalar_one(self) -> str:
        return self.version

    def mappings(self) -> list[dict]:
        return self.rows


class FakeSession:
    def __init__(self, result: FakeResult) -> None:
        self.result = result
        self.statements = []

    async def execute(self, statement):
        self.statements.append(str(statement))
        return self.result


class SQLRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_version_and_explain(self) -> None:
        session = FakeSession(FakeResult())
        repository = SQLRepository(session)

        version = await repository.get_version()
        await repository.explain("SELECT id FROM fact_order")

        self.assertEqual(version, "8.0.36")
        self.assertEqual(session.statements, ["SELECT VERSION()", "EXPLAIN SELECT id FROM fact_order"])

    async def test_execute_returns_mapping_rows(self) -> None:
        session = FakeSession(FakeResult(rows=[{"id": 1, "amount": 99.0}]))

        result = await SQLRepository(session).execute("SELECT id, amount FROM fact_order")

        self.assertEqual(result, [{"id": 1, "amount": 99.0}])
        self.assertEqual(session.statements, ["SELECT id, amount FROM fact_order"])


if __name__ == "__main__":
    unittest.main()
