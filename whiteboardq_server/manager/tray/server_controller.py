"""Server process lifecycle management for tray application."""

import json
import os
import ssl
import subprocess
import sys
import urllib.request
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal


class ServerState(Enum):
    """Server operational state."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class HealthWorker(QObject):
    """Background worker for polling server health endpoint."""

    finished = Signal(bool, int, int)  # is_healthy, clients, uptime

    def __init__(self):
        super().__init__()

    def run(self):
        """Poll health endpoint in background thread."""
        is_healthy, clients, uptime = self._fetch_health()
        self.finished.emit(is_healthy, clients, uptime)

    def _fetch_health(self) -> tuple[bool, int, int]:
        """Fetch health data from server.

        Returns:
            Tuple of (is_healthy, client_count, uptime_seconds)
        """
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://localhost:5000/health"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req, timeout=2, context=ctx) as response:
                data = json.loads(response.read().decode())
                checks = data.get("checks", {})
                clients = checks.get("connected_clients", 0)
                uptime = data.get("uptime_seconds", 0)
                return True, clients, uptime
        except Exception:
            return False, -1, -1


class ServerController(QObject):
    """Controls the WhiteboardQ server process lifecycle.

    Provides start/stop control and status monitoring for the server
    process, with signals for status changes.

    Signals:
        status_changed(state, clients, uptime): Emitted when server status changes
        error_occurred(message): Emitted when an error occurs
    """

    status_changed = Signal(ServerState, int, int)  # state, clients, uptime
    error_occurred = Signal(str)  # error message

    def __init__(self, parent=None):
        super().__init__(parent)

        self._server_process = None
        self._state = ServerState.STOPPED
        self._clients = 0
        self._uptime = 0

        # Health polling
        self._health_thread = None
        self._health_worker = None
        self._health_check_pending = False
        self._stop_attempt_count = 0

        # Poll timer (every 5 seconds)
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._start_health_check)

    @property
    def state(self) -> ServerState:
        """Current server state."""
        return self._state

    @property
    def clients(self) -> int:
        """Current connected client count."""
        return self._clients

    @property
    def uptime(self) -> int:
        """Current server uptime in seconds."""
        return self._uptime

    @property
    def is_running(self) -> bool:
        """Whether server is running."""
        return self._state == ServerState.RUNNING

    def start(self):
        """Start the server process.

        Starts the server with CREATE_NO_WINDOW flag so no console
        window is visible (tray mode operation).
        """
        if self._state in (ServerState.RUNNING, ServerState.STARTING):
            return

        # Check if service is running (conflict check)
        if self._is_service_running():
            self.error_occurred.emit(
                "WhiteboardQ Windows service is already running.\n"
                "Stop the service first, or use the service to manage the server."
            )
            return

        # Check for existing process
        if self._is_any_process_running():
            self.error_occurred.emit("Server process is already running.")
            return

        server_exe = self._get_server_exe_path()
        if not server_exe.exists():
            self.error_occurred.emit(f"Server executable not found at:\n{server_exe}")
            return

        self._set_state(ServerState.STARTING)

        try:
            # Build environment for server process
            env = os.environ.copy()

            # Per spec: Always use %ProgramData%\WhiteboardQ\ for data files
            # - whiteboardq.db (SQLite database)
            # - config.json (server configuration)
            # - logs/server.log
            program_data = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
            whiteboardq_dir = program_data / "WhiteboardQ"

            env["WHITEBOARD_DATA_DIR"] = str(whiteboardq_dir)
            env["WHITEBOARD_DB"] = str(whiteboardq_dir / "whiteboardq.db")
            env["WHITEBOARD_CERT"] = str(whiteboardq_dir / "certs" / "cert.pem")
            env["WHITEBOARD_KEY"] = str(whiteboardq_dir / "certs" / "key.pem")

            # Start server with hidden console window
            self._server_process = subprocess.Popen(
                [str(server_exe)],
                cwd=str(server_exe.parent),
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Start polling to detect when server is ready
            self._poll_timer.start(1000)  # Check every second while starting

        except Exception as e:
            self._set_state(ServerState.STOPPED)
            self.error_occurred.emit(f"Failed to start server: {e}")

    def stop(self):
        """Stop the server process."""
        # Check if service is running (we can't stop that)
        if self._is_service_running() and not self._is_our_process_running():
            self.error_occurred.emit(
                "Server is running as a Windows service.\n"
                "Use services.msc or the service scripts to stop it."
            )
            return

        # Check if anything is actually running
        if not self._is_any_process_running() and self._state == ServerState.STOPPED:
            return  # Nothing to stop

        # Stop health polling during shutdown to prevent interference
        self._poll_timer.stop()

        self._set_state(ServerState.STOPPING)
        self._stop_attempt_count = 0
        self._do_stop()

    def _do_stop(self):
        """Actually perform the stop operation."""
        self._stop_attempt_count += 1

        # Always use taskkill /F for reliable termination
        try:
            subprocess.run(
                ["taskkill", "/IM", "WhiteboardQ-Server.exe", "/F"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass

        # Clear our process reference
        self._server_process = None

        # Check if it actually stopped
        QTimer.singleShot(500, self._check_stopped)

    def start_monitoring(self):
        """Start the health monitoring timer."""
        if not self._poll_timer.isActive():
            self._poll_timer.start(5000)  # Poll every 5 seconds
            self._start_health_check()

    def stop_monitoring(self):
        """Stop the health monitoring timer."""
        self._poll_timer.stop()

    def _set_state(self, state: ServerState):
        """Update state and emit signal."""
        self._state = state
        self.status_changed.emit(state, self._clients, self._uptime)

    def _check_stopped(self):
        """Verify server has stopped."""
        if not self._is_any_process_running():
            self._clients = 0
            self._uptime = 0
            self._set_state(ServerState.STOPPED)
            # Resume health monitoring (will detect external starts)
            self._poll_timer.start(5000)
        else:
            # Still running - retry kill up to 5 times
            if self._stop_attempt_count < 5:
                self._do_stop()
            else:
                # Give up after 5 attempts
                self.error_occurred.emit(
                    "Failed to stop server process after multiple attempts.\n"
                    "Try stopping it manually via Task Manager."
                )
                self._set_state(ServerState.RUNNING)
                self._poll_timer.start(5000)

    def _start_health_check(self):
        """Start background health check."""
        if self._health_check_pending:
            return

        self._health_check_pending = True

        self._health_thread = QThread()
        self._health_worker = HealthWorker()
        self._health_worker.moveToThread(self._health_thread)

        self._health_thread.started.connect(self._health_worker.run)
        self._health_worker.finished.connect(self._on_health_result)
        self._health_worker.finished.connect(self._health_thread.quit)
        self._health_thread.finished.connect(self._cleanup_health_thread)

        self._health_thread.start()

    def _on_health_result(self, is_healthy: bool, clients: int, uptime: int):
        """Handle health check result."""
        self._health_check_pending = False

        # Ignore health results when stopping - we're shutting down
        if self._state == ServerState.STOPPING:
            return

        if is_healthy:
            self._clients = clients
            self._uptime = uptime

            if self._state == ServerState.STARTING:
                # Server is now ready
                self._poll_timer.setInterval(5000)  # Normal polling interval
                self._set_state(ServerState.RUNNING)
            elif self._state == ServerState.STOPPED:
                # Server came back (maybe started externally)
                self._set_state(ServerState.RUNNING)
            else:
                # Just emit update with new stats
                self.status_changed.emit(self._state, clients, uptime)
        else:
            # Health check failed
            if self._state == ServerState.RUNNING:
                # Server may have crashed
                if not self._is_any_process_running():
                    self._clients = 0
                    self._uptime = 0
                    self._set_state(ServerState.STOPPED)
            elif self._state == ServerState.STARTING:
                # Still starting, keep polling
                if not self._is_our_process_running():
                    # Process died during startup
                    self._set_state(ServerState.STOPPED)
                    self.error_occurred.emit("Server process exited during startup")

    def _cleanup_health_thread(self):
        """Clean up health thread objects."""
        if self._health_thread:
            self._health_thread.deleteLater()
            self._health_thread = None
        if self._health_worker:
            self._health_worker.deleteLater()
            self._health_worker = None

    def _get_server_exe_path(self) -> Path:
        """Get path to WhiteboardQ-Server.exe."""
        if getattr(sys, "frozen", False):
            # Running as compiled exe - server is in same folder
            return Path(sys.executable).parent / "WhiteboardQ-Server.exe"
        else:
            # Development mode - check dist folder first, then try running from source
            dist_exe = Path(__file__).parent.parent.parent.parent / "dist" / "WhiteboardQ-Server.exe"
            if dist_exe.exists():
                return dist_exe
            # Fallback: could run server from source, but that's not supported in tray mode
            return dist_exe

    def _is_service_running(self) -> bool:
        """Check if WhiteboardQ Windows service is running."""
        try:
            result = subprocess.run(
                ["sc", "query", "WhiteboardQServer"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return "RUNNING" in result.stdout
        except Exception:
            return False

    def _is_our_process_running(self) -> bool:
        """Check if our tracked server process is running."""
        return self._server_process is not None and self._server_process.poll() is None

    def _is_any_process_running(self) -> bool:
        """Check if any WhiteboardQ server process is running."""
        if self._is_our_process_running():
            return True

        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WhiteboardQ-Server.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = result.stdout.strip().split("\n")
            return len(lines) > 1 and "WhiteboardQ-Server.exe" in result.stdout
        except Exception:
            return False
