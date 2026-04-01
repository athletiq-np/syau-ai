import asyncio
from collections import defaultdict
from typing import Dict, Set
from fastapi import WebSocket
import structlog

log = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        # job_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, job_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[job_id].add(ws)
        log.info("ws_connected", job_id=job_id, total=len(self._connections[job_id]))

    def disconnect(self, job_id: str, ws: WebSocket) -> None:
        self._connections[job_id].discard(ws)
        if not self._connections[job_id]:
            del self._connections[job_id]
        log.info("ws_disconnected", job_id=job_id)

    async def broadcast(self, job_id: str, message: dict) -> None:
        conns = list(self._connections.get(job_id, []))
        if not conns:
            return
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)


manager = ConnectionManager()
