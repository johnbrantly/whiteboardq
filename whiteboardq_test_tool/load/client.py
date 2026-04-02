"""Simulated WebSocket client for load testing."""

import asyncio
import json
import ssl
import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote

from websockets.client import connect
from websockets.exceptions import ConnectionClosed


@dataclass
class ClientConfig:
    """Configuration for a simulated client."""

    server_url: str
    station_name: str
    message_rate: float = 1.0  # messages per second
    include_deletions: bool = False
    verify_ssl: bool = False


@dataclass
class ClientMetrics:
    """Metrics collected during client operation."""

    messages_sent: int = 0
    messages_received: int = 0
    deletions_sent: int = 0
    connect_time_ms: float = 0
    latencies: List[float] = field(default_factory=list)
    errors: int = 0


class SimulatedClient:
    """Simulated WebSocket client for load testing."""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.metrics = ClientMetrics()
        self._running = False
        self._ws = None
        self._pending_acks = {}  # content -> send_time (for latency tracking)
        self._message_ids = []  # Track created message IDs for deletion

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for wss:// connections."""
        if not self.config.server_url.startswith("wss://"):
            return None

        ctx = ssl.create_default_context()
        if not self.config.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    async def run(self, duration: float) -> ClientMetrics:
        """
        Run client for specified duration.

        Args:
            duration: How long to run in seconds

        Returns:
            Collected metrics
        """
        self._running = True
        url = f"{self.config.server_url}?station={quote(self.config.station_name)}"
        ssl_ctx = self._create_ssl_context()

        # Track connection time
        start = time.perf_counter()

        try:
            async with connect(url, ssl=ssl_ctx) as ws:
                self._ws = ws
                self.metrics.connect_time_ms = (time.perf_counter() - start) * 1000

                # Run send/receive tasks concurrently
                end_time = time.time() + duration

                send_task = asyncio.create_task(self._send_loop(end_time))
                recv_task = asyncio.create_task(self._receive_loop(end_time))

                await asyncio.gather(send_task, recv_task)

        except ConnectionClosed as e:
            # Normal close or server-initiated close
            pass
        except Exception as e:
            self.metrics.errors += 1

        self._running = False
        return self.metrics

    async def _send_loop(self, end_time: float) -> None:
        """Send messages at configured rate."""
        if self.config.message_rate <= 0:
            return

        interval = 1.0 / self.config.message_rate
        msg_counter = 0

        while time.time() < end_time and self._running:
            msg_counter += 1
            content = f"[{self.config.station_name}] Test message #{msg_counter}"

            # Send create_message
            try:
                await self._ws.send(json.dumps({
                    "type": "create_message",
                    "content": content,
                }))
                self._pending_acks[content] = time.perf_counter()
                self.metrics.messages_sent += 1
            except Exception:
                self.metrics.errors += 1
                break

            await asyncio.sleep(interval)

    async def _receive_loop(self, end_time: float) -> None:
        """Receive and process server messages."""
        while time.time() < end_time and self._running:
            try:
                msg = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=1.0
                )
                data = json.loads(msg)
                self.metrics.messages_received += 1

                event_type = data.get("type")

                # Track latency for our messages
                if event_type == "message_created":
                    message = data.get("message", data)
                    content = message.get("content", "")
                    message_id = message.get("id")

                    # Check if this is our message
                    if content in self._pending_acks:
                        latency = (time.perf_counter() - self._pending_acks.pop(content)) * 1000
                        self.metrics.latencies.append(latency)

                        # Track for potential deletion
                        if message_id and self.config.include_deletions:
                            self._message_ids.append(message_id)

                            # Delete older messages to avoid buildup
                            if len(self._message_ids) > 5:
                                old_id = self._message_ids.pop(0)
                                try:
                                    await self._ws.send(json.dumps({
                                        "type": "delete_message",
                                        "message_id": old_id,
                                    }))
                                    self.metrics.deletions_sent += 1
                                except Exception:
                                    pass

            except asyncio.TimeoutError:
                continue
            except ConnectionClosed:
                break
            except Exception:
                self.metrics.errors += 1
