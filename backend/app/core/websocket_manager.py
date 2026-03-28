from collections import defaultdict
import asyncio
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(list)

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[meeting_id].append(websocket)

    def disconnect(self, meeting_id: str, websocket: WebSocket):
        if meeting_id in self.active_connections:
            self.active_connections[meeting_id] = [
                ws for ws in self.active_connections[meeting_id] if ws != websocket
            ]

            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]

    async def _safe_send_json(self, meeting_id: str, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            self.disconnect(meeting_id, websocket)
            return False

    async def broadcast(self, meeting_id: str, message: dict):
        connections = list(self.active_connections.get(meeting_id, []))
        if not connections:
            return

        tasks = [
            self._safe_send_json(meeting_id, ws, message)
            for ws in connections
        ]

        await asyncio.gather(*tasks, return_exceptions=True)


manager = ConnectionManager()