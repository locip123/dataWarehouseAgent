import unittest
from collections.abc import AsyncIterator
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from app.router import query_router
from app.services.agent import query_service


class FakeGraph:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self.events = events
        self.input: dict[str, str] | None = None
        self.stream_mode: list[str] | None = None

    async def astream(
        self, input: dict[str, str], *, stream_mode: list[str]
    ) -> AsyncIterator[tuple[str, object]]:
        self.input = input
        self.stream_mode = stream_mode
        for event in self.events:
            yield event


class FailingGraph:
    async def astream(
        self, input: dict[str, str], *, stream_mode: list[str]
    ) -> AsyncIterator[tuple[str, object]]:
        raise RuntimeError("graph failed")
        yield "custom", {}


class QueryServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_query_forwards_progress_and_sql_result(self) -> None:
        graph = FakeGraph(
            [
                ("custom", {"type": "progress", "step": "生成SQL", "status": "running"}),
                ("updates", {"generate_sql": {"sql": "SELECT 1"}}),
                ("updates", {"execute_sql": {"sql_result": [{"total": 1}]}}),
            ]
        )

        with patch.object(query_service, "graph", graph):
            events = [event async for event in query_service.stream_query("订单数")]

        self.assertEqual(graph.input, {"query": "订单数"})
        self.assertEqual(graph.stream_mode, ["custom", "updates"])
        self.assertEqual(
            events,
            [
                {"type": "progress", "step": "生成SQL", "status": "running"},
                {"type": "result", "data": [{"total": 1}]},
            ],
        )

    async def test_stream_query_returns_terminal_error(self) -> None:
        with patch.object(query_service, "graph", FailingGraph()), patch.object(
            query_service.logger, "exception"
        ) as log_exception:
            events = [event async for event in query_service.stream_query("订单数")]

        self.assertEqual(events, [{"type": "error", "message": "graph failed"}])
        log_exception.assert_called_once_with("数据查询失败")


class QueryAPITest(unittest.TestCase):
    def test_query_endpoint_returns_sse(self) -> None:
        async def fake_stream_query(query: str) -> AsyncIterator[dict[str, object]]:
            self.assertEqual(query, "订单数")
            yield {"type": "progress", "step": "生成SQL", "status": "success"}
            yield {"type": "result", "data": [{"total": 1}]}

        with patch.object(query_router, "stream_query", fake_stream_query):
            response = TestClient(main.app).post("/api/query", json={"query": "订单数"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/event-stream; charset=utf-8")
        self.assertIn('data: {"type": "progress"', response.text)
        self.assertIn('data: {"type": "result"', response.text)

    def test_query_endpoint_rejects_empty_query(self) -> None:
        response = TestClient(main.app).post("/api/query", json={"query": ""})

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
