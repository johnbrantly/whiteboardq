"""WebSocket connection manager — tracks clients and broadcasts events."""

import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time messaging."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, station_name: str) -> None:
        """
        Accept a new WebSocket connection.
        If station_name already exists, disconnects the old connection first.
        """
        # Disconnect existing connection with same station name
        if station_name in self.active_connections:
            old_ws = self.active_connections[station_name]
            logger.debug(f"Disconnecting existing connection for station: {station_name}")
            try:
                if old_ws.client_state == WebSocketState.CONNECTED:
                    await old_ws.close(code=1000, reason="Replaced by new connection")
            except (ConnectionClosed, RuntimeError) as e:
                logger.debug(f"Error closing old connection: {e}")

        await websocket.accept()
        self.active_connections[station_name] = websocket
        logger.debug(f"Station connected: {station_name} (total: {len(self.active_connections)})")

    def disconnect(self, station_name: str) -> None:
        """Remove a connection from the active pool."""
        if station_name in self.active_connections:
            del self.active_connections[station_name]
            logger.debug(f"Station disconnected: {station_name} (total: {len(self.active_connections)})")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Send an event to all connected clients."""
        disconnected = []
        for station_name, websocket in self.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(event)
            except (ConnectionClosed, RuntimeError) as e:
                logger.debug(f"Error sending to {station_name}: {e}")
                disconnected.append(station_name)

        # Clean up any failed connections
        for station_name in disconnected:
            self.disconnect(station_name)

    async def send_personal(self, station_name: str, event: dict[str, Any]) -> None:
        """Send an event to a specific client."""
        if station_name in self.active_connections:
            websocket = self.active_connections[station_name]
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(event)
            except (ConnectionClosed, RuntimeError) as e:
                logger.debug(f"Error sending to {station_name}: {e}")
                self.disconnect(station_name)

    @property
    def connected_stations(self) -> list[str]:
        """Get list of connected station names."""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()
