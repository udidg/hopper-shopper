"""WebSocket connection manager – tracks connections per list_id."""

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections grouped by list_id."""

    def __init__(self):
        # list_id → set of active WebSocket connections
        self._connections: dict[int, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, list_id: int) -> None:
        """Accept a WebSocket connection and register it for a list."""
        await websocket.accept()
        if list_id not in self._connections:
            self._connections[list_id] = set()
        self._connections[list_id].add(websocket)

    def disconnect(self, websocket: WebSocket, list_id: int) -> None:
        """Remove a WebSocket connection from a list."""
        if list_id in self._connections:
            self._connections[list_id].discard(websocket)
            if not self._connections[list_id]:
                del self._connections[list_id]

    async def broadcast(
        self,
        list_id: int,
        message: dict[str, Any],
        exclude: WebSocket | None = None,
    ) -> None:
        """
        Broadcast a JSON message to all connections for a list.

        Optionally exclude the sender's connection.
        """
        if list_id not in self._connections:
            return

        payload = json.dumps(message)
        dead_connections = []

        for connection in self._connections[list_id]:
            if connection is exclude:
                continue
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self._connections[list_id].discard(conn)

    async def send_personal(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> None:
        """Send a JSON message to a single connection."""
        await websocket.send_text(json.dumps(message))

    def get_connection_count(self, list_id: int) -> int:
        """Return the number of active connections for a list."""
        return len(self._connections.get(list_id, set()))


# Singleton instance
manager = ConnectionManager()
