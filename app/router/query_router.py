import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent import stream_query


router = APIRouter(prefix="/api")


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)


async def _sse_events(query: str) -> AsyncIterator[str]:
    async for event in stream_query(query):
        yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


@router.post("/query")
async def query(request: QueryRequest) -> StreamingResponse:
    return StreamingResponse(
        _sse_events(request.query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
