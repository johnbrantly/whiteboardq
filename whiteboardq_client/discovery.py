"""UDP discovery client for finding servers on the LAN."""

import logging
import socket
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 5001
DISCOVERY_REQUEST = b"WBDQ_DISCOVER"
DISCOVERY_RESPONSE_PREFIX = "WBDQ_SERVER"


@dataclass
class DiscoveredServer:
    """A server discovered via UDP broadcast."""

    host: str
    port: int

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


def _get_local_interfaces() -> list[tuple[str, str]]:
    """Get list of local IPv4 interfaces with their broadcast addresses.

    Returns:
        List of (local_ip, broadcast_ip) tuples for each interface.
        Uses /24 subnet assumption (x.x.x.255) which covers most networks.
    """
    interfaces = []

    try:
        # Get all IPs associated with hostname
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)

        for ip in ip_list:
            # Skip loopback
            if ip.startswith("127."):
                continue

            # Calculate broadcast address assuming /24 subnet
            parts = ip.split(".")
            if len(parts) == 4:
                broadcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                interfaces.append((ip, broadcast))
                logger.debug(f"Found interface: {ip} -> broadcast {broadcast}")

    except socket.error as e:
        logger.warning(f"Failed to enumerate interfaces via gethostbyname_ex: {e}")

    # Fallback: try connecting to external IP to find default route
    if not interfaces:
        try:
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_sock.connect(("8.8.8.8", 80))
            local_ip = temp_sock.getsockname()[0]
            temp_sock.close()

            parts = local_ip.split(".")
            if len(parts) == 4:
                broadcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                interfaces.append((local_ip, broadcast))
                logger.debug(f"Found interface via default route: {local_ip} -> broadcast {broadcast}")

        except socket.error as e:
            logger.warning(f"Failed to find default interface: {e}")

    return interfaces


def _get_broadcast_addresses() -> list[str]:
    """Get list of broadcast addresses to send discovery to.

    Returns:
        List of broadcast addresses (always includes 255.255.255.255)
    """
    broadcasts = set()

    # Always include limited broadcast
    broadcasts.add("255.255.255.255")

    # Add directed broadcast for each interface
    for local_ip, broadcast_ip in _get_local_interfaces():
        broadcasts.add(broadcast_ip)

    result = list(broadcasts)
    logger.debug(f"Broadcast addresses to try: {result}")
    return result


def discover_servers(timeout: float = 2.0) -> list[DiscoveredServer]:
    """Broadcast discovery request and collect server responses.

    Sends discovery broadcasts to all local network interfaces to support
    multi-homed systems (multiple NICs, VPNs, virtual networks like ZeroTier).

    Args:
        timeout: How long to wait for responses (seconds)

    Returns:
        List of discovered servers (empty if none found)
    """
    servers: dict[str, DiscoveredServer] = {}  # Key by host:port for deduplication

    logger.info(f"Starting server discovery (timeout={timeout}s)")

    # Get all broadcast addresses to try
    broadcast_addresses = _get_broadcast_addresses()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)  # Short timeout for individual receives

        # Send discovery request to all broadcast addresses
        for broadcast_addr in broadcast_addresses:
            try:
                sock.sendto(DISCOVERY_REQUEST, (broadcast_addr, DISCOVERY_PORT))
                logger.debug(f"Sent discovery broadcast to {broadcast_addr}:{DISCOVERY_PORT}")
            except OSError as e:
                logger.warning(f"Failed to send to {broadcast_addr}: {e}")

        # Collect responses for the timeout period
        end_time = time.time() + timeout

        while time.time() < end_time:
            try:
                data, addr = sock.recvfrom(1024)
                response = data.decode("utf-8", errors="ignore")
                logger.debug(f"Received response from {addr[0]}:{addr[1]}: {response}")

                # Parse WBDQ_SERVER|host|port
                # Note: We use addr[0] (source IP of response) instead of the
                # hostname in the message. This guarantees we connect to the
                # correct interface on multi-homed servers.
                if response.startswith(DISCOVERY_RESPONSE_PREFIX + "|"):
                    parts = response.split("|")
                    if len(parts) == 3:
                        host = addr[0]  # Use source IP, not message content
                        try:
                            port = int(parts[2])
                            key = f"{host}:{port}"
                            if key not in servers:
                                servers[key] = DiscoveredServer(host=host, port=port)
                                logger.info(f"Discovered server: {host}:{port}")
                        except ValueError:
                            logger.warning(f"Invalid port in response: {parts[2]}")
                else:
                    logger.debug(f"Ignoring non-discovery response: {response[:50]}")

            except socket.timeout:
                continue  # Keep waiting until end_time
            except OSError as e:
                logger.warning(f"Socket error during receive: {e}")
                break  # Socket error, stop listening

    except OSError as e:
        logger.error(f"Failed to create/use discovery socket: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass

    logger.info(f"Discovery complete: found {len(servers)} server(s)")
    return list(servers.values())


def test_connection(host: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    """Test TLS connection to a server.

    Args:
        host: Server hostname or IP
        port: Server port
        timeout: Connection timeout in seconds

    Returns:
        (success: bool, message: str)
    """
    import ssl

    logger.info(f"Testing connection to {host}:{port}")

    try:
        # Validate port
        if not (1 <= port <= 65535):
            logger.warning(f"Invalid port: {port}")
            return False, f"Invalid port: {port}"

        # Try to resolve hostname
        try:
            resolved = socket.gethostbyname(host)
            logger.debug(f"Resolved {host} -> {resolved}")
        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed for {host}: {e}")
            return False, f"Unknown host: {host}"

        # Create SSL context that accepts self-signed certs
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Attempt TLS connection (same as what wss:// uses)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            logger.debug(f"Attempting TCP connect to {host}:{port}")
            sock.connect((host, port))
            logger.debug(f"TCP connected, starting TLS handshake")
            # Wrap with TLS
            ssl_sock = ssl_context.wrap_socket(sock, server_hostname=host)
            ssl_sock.close()
            logger.info(f"Connection test successful: {host}:{port}")
            return True, f"Connected to {host}:{port} (TLS OK)"
        except socket.timeout:
            logger.warning(f"Connection timed out: {host}:{port}")
            return False, f"Connection timed out: {host}:{port}"
        except ConnectionRefusedError:
            logger.warning(f"Connection refused: {host}:{port}")
            return False, f"Connection refused: {host}:{port}"
        except ssl.SSLError as e:
            logger.warning(f"TLS error connecting to {host}:{port}: {e.reason}")
            return False, f"TLS error: {e.reason}"
        except OSError as e:
            logger.warning(f"Cannot reach {host}:{port}: {e}")
            return False, f"Cannot reach {host}:{port}"

    except Exception as e:
        logger.error(f"Unexpected error testing connection: {e}")
        return False, f"Error: {str(e)}"
