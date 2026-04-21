from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, batch_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[batch_id].append(websocket)

    def disconnect(self, batch_id: int, websocket: WebSocket):
        if batch_id in self.active_connections:
            if websocket in self.active_connections[batch_id]:
                self.active_connections[batch_id].remove(websocket)

            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]

    async def broadcast(self, batch_id: int, message: dict):
        if batch_id not in self.active_connections:
            return

        dead = []

        for conn in self.active_connections[batch_id]:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)

        for conn in dead:
            self.disconnect(batch_id, conn)


ws_manager = ConnectionManager()