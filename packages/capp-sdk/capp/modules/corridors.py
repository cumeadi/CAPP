import json
import httpx
from typing import List, AsyncGenerator
from ..models import CorridorStatus, CorridorEvent, CorridorFeedResponse
from .._utils import handle_api_error

class CorridorsModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def status(self, corridor: str) -> CorridorStatus:
        res = await self._client.get(f"/corridors/{corridor}/status")
        handle_api_error(res)
        return CorridorStatus(**res.json())

    async def get_feed(self, corridor: str, lookback_days: int = 7) -> CorridorFeedResponse:
        res = await self._client.get(f"/corridors/feed?corridor={corridor}&lookback_days={lookback_days}")
        handle_api_error(res)
        return CorridorFeedResponse(**res.json())

    async def list(self) -> List[str]:
        res = await self._client.get("/corridors")
        handle_api_error(res)
        return res.json().get("corridors", [])
        
    async def subscribe(self, corridor: str) -> AsyncGenerator[CorridorEvent, None]:
        async with self._client.stream("GET", f"/corridors/{corridor}/events") as response:
            handle_api_error(response)
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        event_data = json.loads(data_str)
                        yield CorridorEvent(**event_data)
                    except json.JSONDecodeError:
                        continue

    async def subscribe_all(self) -> AsyncGenerator[CorridorEvent, None]:
        async with self._client.stream("GET", "/corridors/events") as response:
            handle_api_error(response)
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        event_data = json.loads(data_str)
                        yield CorridorEvent(**event_data)
                    except json.JSONDecodeError:
                        continue
