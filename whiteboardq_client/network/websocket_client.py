"""Async WebSocket client with Qt signals for thread-safe UI updates."""

import asyncio
import json
import logging
import ssl
from typing import Optional
from urllib.parse import quote

from PySide6.QtCore import QObject, Signal
from websockets.client import connect, WebSocketClientProtocol
import socket
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class WebSocketClient(QObject):
    """Async WebSocket client with Qt signals for thread-safe UI updates."""

    # Signals
    server_connected = Signal()
    server_disconnected = Signal()
    messages_loaded = Signal(list)  # Initial messages list
    thresholds_received = Signal(dict)  # Server config thresholds
    message_created = Signal(dict)
    message_updated = Signal(dict)  # For position/important changes
    message_deleted = Signal(str)  # message_id
    message_restored = Signal(dict)
    error = Signal(str)
    connection_error = Signal(str)

    def __init__(self, server_url: str, station_name: str, verify_ssl: bool = False):
        super().__init__()
        self.server_url = server_url
        self.station_name = station_name
        self.verify_ssl = verify_ssl
        self.ws: Optional[WebSocketClientProtocol] = None
        self.running = False
        self._reconnect_delay = 5.0
        self._should_reconnect = True
        self._reconnect_requested = False

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.ws is not None and self.running

    def update_config(self, server_url: str, station_name: str, verify_ssl: bool) -> None:
        """Update connection config (requires reconnect)."""
        self.server_url = server_url
        self.station_name = station_name
        self.verify_ssl = verify_ssl

    def reconnect(self) -> None:
        """Signal that a reconnect is needed with updated config."""
        self._reconnect_requested = True
        # The recv loop in _connect() checks this flag every second and will exit

    async def connect_and_run(self) -> None:
        """Connect to server and process messages. Auto-reconnects on failure."""
        self._should_reconnect = True

        while self._should_reconnect:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.connection_error.emit(str(e))

            if self._should_reconnect:
                logger.info(f"Reconnecting in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for wss:// connections."""
        if not self.server_url.startswith("wss://"):
            return None

        ctx = ssl.create_default_context()
        if not self.verify_ssl:
            # Accept self-signed certificates
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    async def _connect(self) -> None:
        """Single connection attempt."""
        url = f"{self.server_url}/ws?station={quote(self.station_name)}"
        logger.info(f"Connecting to {url}")

        ssl_context = self._create_ssl_context()

        try:
            # Force IPv4 to avoid issues with IPv6 link-local addresses missing zone IDs
            async with connect(url, ssl=ssl_context, family=socket.AF_INET) as ws:
                self.ws = ws
                self.running = True
                self._reconnect_requested = False  # Clear on successful connect
                self.server_connected.emit()
                logger.info("Connected")

                while True:
                    # Use wait_for with timeout to periodically check reconnect flag
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # Check if reconnect was requested
                        if self._reconnect_requested:
                            logger.info("Reconnect requested, closing connection")
                            break
                        continue

                    try:
                        event = json.loads(message)
                        self._handle_event(event)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")

        except ConnectionClosed as e:
            logger.warning(f"Connection closed: code={e.code}, reason={e.reason}")
        except WebSocketException as e:
            logger.error(f"WebSocket error: {type(e).__name__}: {e}")
            self.error.emit(str(e))
        except ssl.SSLError as e:
            logger.error(f"SSL/TLS error: {e.reason} - {e}")
            self.connection_error.emit(f"TLS error: {e.reason}")
        except OSError as e:
            logger.error(f"Connection failed: {type(e).__name__}: {e}")
            self.connection_error.emit(str(e))
        finally:
            self.ws = None
            self.running = False
            self.server_disconnected.emit()
            logger.info("Disconnected")

    def _handle_event(self, event: dict) -> None:
        """Dispatch event to appropriate signal."""
        event_type = event.get("type")
        logger.debug(f"Received event: {event_type}")

        if event_type == "initial_state":
            # Extract messages and config from initial state
            messages = event.get("messages", [])
            config = event.get("config", {})
            self.messages_loaded.emit(messages)
            if config:
                self.thresholds_received.emit(config)
        elif event_type == "message_created":
            message = event.get("message", event)
            self.message_created.emit(message)
        elif event_type == "message_moved":
            # Server sends all_positions with updated positions for all affected messages
            all_positions = event.get("all_positions", [])
            for pos_update in all_positions:
                self.message_updated.emit(pos_update)
        elif event_type == "message_updated":
            message = event.get("message", event)
            self.message_updated.emit(message)
        elif event_type == "message_deleted":
            message_id = event.get("message_id") or event.get("id")
            if message_id:
                self.message_deleted.emit(message_id)
        elif event_type == "message_restored":
            message = event.get("message", event)
            self.message_restored.emit(message)
        elif event_type == "config_changed":
            # Server config updated - emit thresholds signal
            config = event.get("config", {})
            if config:
                self.thresholds_received.emit(config)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    async def send(self, event: dict) -> None:
        """Send event to server."""
        if self.ws:
            try:
                await self.ws.send(json.dumps(event))
            except Exception as e:
                logger.error(f"Send error: {e}")
                self.error.emit(str(e))

    async def _create_message(self, content: str) -> None:
        """Send create_message event."""
        await self.send({
            "type": "create_message",
            "content": content
        })

    async def _move_message(self, message_id: str, direction: str) -> None:
        """Send move_message event. Direction: up, down, top."""
        await self.send({
            "type": "move_message",
            "message_id": message_id,
            "direction": direction
        })

    async def _delete_message(self, message_id: str) -> None:
        """Send delete_message event."""
        await self.send({
            "type": "delete_message",
            "message_id": message_id
        })

    async def _restore_message(self, message_id: str) -> None:
        """Send restore_message event."""
        await self.send({
            "type": "restore_message",
            "message_id": message_id
        })

    async def _update_message(self, message_id: str, **kwargs) -> None:
        """Send update_message event (for is_important, etc)."""
        await self.send({
            "type": "update_message",
            "message_id": message_id,
            **kwargs
        })

    async def _wipe_all(self) -> None:
        """Send wipe_all event to delete all messages."""
        await self.send({"type": "wipe_all"})

    async def _restore_wipe(self) -> None:
        """Send restore_wipe event to restore messages from last wipe."""
        await self.send({"type": "restore_wipe"})

    # Synchronous wrapper methods for UI calls
    def create_message(self, content: str) -> None:
        """Send create_message event (sync wrapper)."""
        asyncio.create_task(self._create_message(content))

    def move_message(self, message_id: str, direction: str) -> None:
        """Send move_message event (sync wrapper)."""
        asyncio.create_task(self._move_message(message_id, direction))

    def delete_message(self, message_id: str) -> None:
        """Send delete_message event (sync wrapper)."""
        asyncio.create_task(self._delete_message(message_id))

    def restore_message(self, message_id: str) -> None:
        """Send restore_message event (sync wrapper)."""
        asyncio.create_task(self._restore_message(message_id))

    def update_message(self, message_id: str, **kwargs) -> None:
        """Send update_message event (sync wrapper)."""
        asyncio.create_task(self._update_message(message_id, **kwargs))

    def wipe_all(self) -> None:
        """Send wipe_all event (sync wrapper)."""
        asyncio.create_task(self._wipe_all())

    def restore_wipe(self) -> None:
        """Send restore_wipe event (sync wrapper)."""
        asyncio.create_task(self._restore_wipe())

    async def connect_once(self) -> None:
        """Connect to server (single attempt)."""
        await self._connect()

    async def wait_before_reconnect(self, delay: float = 3.0) -> None:
        """Wait before reconnecting, but wake early if reconnect() was called."""
        # Poll with short sleeps so we can respond to reconnect requests quickly
        elapsed = 0.0
        interval = 0.1
        while elapsed < delay:
            if self._reconnect_requested:
                self._reconnect_requested = False
                return
            await asyncio.sleep(interval)
            elapsed += interval

    async def wait_disconnected(self) -> None:
        """Wait until disconnected."""
        while self.running:
            await asyncio.sleep(0.1)

    def disconnect(self) -> None:
        """Disconnect from server."""
        self.stop()

    def stop(self) -> None:
        """Stop reconnection attempts and close connection."""
        self._should_reconnect = False
        if self.ws:
            asyncio.create_task(self.ws.close())
