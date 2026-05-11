import asyncio
from typing import Any

from fastapi import WebSocket

__all__ = ("ViewerBroadcastHub",)


class ViewerBroadcastHub:

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[dict[str, Any]] | None = None

    def bind_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=256)

    @staticmethod
    def format_ws_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {**snapshot, "type": "snapshot"}

    def _enqueue_threadsafe(self, payload: dict[str, Any]) -> None:
        loop = self._loop
        queue = self._queue
        if loop is None or queue is None:
            return

        def _try_put() -> None:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

        try:
            loop.call_soon_threadsafe(_try_put)
        except RuntimeError:
            pass

    def publish_snapshot_threadsafe(self, snapshot: dict[str, Any]) -> None:
        self._enqueue_threadsafe(self.format_ws_snapshot(snapshot))

    def publish_mod_logs_threadsafe(self, entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        self._enqueue_threadsafe({"type": "mod_logs", "entries": entries})

    def publish_tick_frame_threadsafe(self, tick: dict[str, Any], world: dict[str, Any]) -> None:
        self._enqueue_threadsafe({"type": "tick_frame", "tick": tick, "world": world})

    async def run_broadcast_consumer(self) -> None:
        assert self._queue is not None
        while True:
            snap = await self._queue.get()
            await self.broadcast_json(snap)

    async def register(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast_json(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            conns = list(self._connections)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except (ConnectionError, OSError, RuntimeError):
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
