"""UDP discovery responder for LAN server discovery."""

import logging
import socket
import threading

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 5001
DISCOVERY_REQUEST = b"WBDQ_DISCOVER"
DISCOVERY_RESPONSE_PREFIX = "WBDQ_SERVER"


class DiscoveryResponder:
    """Responds to UDP discovery broadcasts from clients.

    Listens on UDP port 5001 for WBDQ_DISCOVER messages and responds
    with WBDQ_SERVER|<host>|<port> to allow clients to find the server.
    """

    def __init__(self, port: int):
        """Initialize the discovery responder.

        Args:
            port: The server's HTTP/WebSocket port to advertise
        """
        self.port = port
        self._running = False
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None
        self._host = self._resolve_host()

    def _resolve_host(self) -> str:
        """Get hostname for logging/display purposes.

        Note: Clients use the source IP of the response packet (addr[0] from
        recvfrom), not this hostname. This is just included in the message
        for logging and potential future display purposes.
        """
        try:
            return socket.gethostname()
        except socket.error:
            return "unknown"

    def start(self) -> None:
        """Start the discovery responder in a background thread."""
        if self._running:
            logger.warning("Discovery responder already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(f"Discovery responder started on UDP port {DISCOVERY_PORT}")

    def stop(self) -> None:
        """Stop the discovery responder."""
        if not self._running:
            return

        self._running = False

        # Close the socket to unblock recvfrom
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        logger.info("Discovery responder stopped")

    def _listen(self) -> None:
        """Main listening loop (runs in background thread)."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(1.0)  # Allow periodic check of _running flag
            self._socket.bind(("", DISCOVERY_PORT))

            logger.debug(f"Discovery socket bound to port {DISCOVERY_PORT}")

            while self._running:
                try:
                    data, addr = self._socket.recvfrom(1024)

                    if data == DISCOVERY_REQUEST:
                        logger.debug(f"Discovery request from {addr[0]}:{addr[1]}")
                        response = f"{DISCOVERY_RESPONSE_PREFIX}|{self._host}|{self.port}"
                        self._socket.sendto(response.encode(), addr)
                        logger.debug(f"Sent discovery response: {response}")

                except socket.timeout:
                    # Normal timeout, just loop to check _running
                    continue
                except OSError:
                    # Socket was closed
                    if self._running:
                        logger.debug("Socket closed unexpectedly")
                    break

        except OSError as e:
            if self._running:
                logger.error(f"Discovery responder error: {e}")
        finally:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
