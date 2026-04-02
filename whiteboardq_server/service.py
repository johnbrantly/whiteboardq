"""Windows Service wrapper for WhiteboardQ Server.

This module allows WhiteboardQ Server to run as a Windows Service.
Install with: WhiteboardQ-Server.exe install
Remove with: WhiteboardQ-Server.exe remove
"""

import os
import sys
import socket
import threading
import logging
from pathlib import Path

import win32serviceutil
import win32service
import win32event
import servicemanager


class WhiteboardQService(win32serviceutil.ServiceFramework):
    """Windows Service that runs the WhiteboardQ FastAPI server."""

    _svc_name_ = "WhiteboardQServer"
    _svc_display_name_ = "WhiteboardQ Server"
    _svc_description_ = "WhiteboardQ office communication server"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server_thread = None
        self.server = None

    def SvcStop(self):
        """Called when the service is asked to stop."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

        # Stop uvicorn server
        if self.server:
            self.server.should_exit = True

    def SvcDoRun(self):
        """Called when the service is asked to start."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        # Set up environment for server
        self._setup_environment()

        # Run the server
        self.main()

    def _setup_environment(self):
        """Configure environment variables for the server."""
        # Use %ProgramData%\WhiteboardQ\ for all data files
        program_data = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
        data_dir = program_data / "WhiteboardQ"

        os.environ["WHITEBOARD_DATA_DIR"] = str(data_dir)
        os.environ["WHITEBOARD_DB"] = str(data_dir / "whiteboardq.db")
        os.environ["WHITEBOARD_CERT"] = str(data_dir / "certs" / "cert.pem")
        os.environ["WHITEBOARD_KEY"] = str(data_dir / "certs" / "key.pem")

        # Set up logging to file (service has no console)
        self._setup_logging(data_dir)

    def _setup_logging(self, data_dir: Path):
        """Configure logging for service mode."""
        from logging.handlers import RotatingFileHandler

        log_dir = data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "server.log"

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        # File handler with rotation
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        logging.info("WhiteboardQ Server service starting...")

    def main(self):
        """Run the FastAPI server."""
        import uvicorn
        from whiteboardq_server.main import app
        from whiteboardq_server.config import config

        # Auto-generate TLS certs if enabled but missing (same as main.py)
        if config.TLS_ENABLED and (not config.CERT_FILE.exists() or not config.KEY_FILE.exists()):
            logging.info("TLS certificates not found. Generating self-signed certificate...")
            from whiteboardq_server.certs import generate_self_signed_cert
            hostname = socket.gethostname()
            generate_self_signed_cert(
                hostname=hostname,
                output_dir=config.CERT_FILE.parent,
            )

        # Configure uvicorn - disable default logging config for service mode
        uvicorn_config = uvicorn.Config(
            app,
            host=config.HOST,
            port=config.PORT,
            log_config=None,  # Disable uvicorn's logging config (causes issues in service)
            access_log=False,
        )

        # Add TLS if enabled (certs should exist now after auto-generation)
        if config.TLS_ENABLED and config.CERT_FILE.exists() and config.KEY_FILE.exists():
            uvicorn_config.ssl_certfile = str(config.CERT_FILE)
            uvicorn_config.ssl_keyfile = str(config.KEY_FILE)

        self.server = uvicorn.Server(uvicorn_config)

        # Run server (blocks until stopped)
        self.server.run()


def is_service_installed() -> bool:
    """Check if the WhiteboardQ service is installed."""
    try:
        status = win32serviceutil.QueryServiceStatus("WhiteboardQServer")
        return True
    except Exception:
        return False


def get_service_status() -> str:
    """Get current service status.

    Returns:
        One of: 'not_installed', 'stopped', 'starting', 'running', 'stopping'
    """
    try:
        status = win32serviceutil.QueryServiceStatus("WhiteboardQServer")
        state = status[1]

        if state == win32service.SERVICE_STOPPED:
            return "stopped"
        elif state == win32service.SERVICE_START_PENDING:
            return "starting"
        elif state == win32service.SERVICE_RUNNING:
            return "running"
        elif state == win32service.SERVICE_STOP_PENDING:
            return "stopping"
        else:
            return "stopped"
    except Exception:
        return "not_installed"


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Started by Windows Service Control Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WhiteboardQService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line arguments (install, remove, start, stop, etc.)
        win32serviceutil.HandleCommandLine(WhiteboardQService)
