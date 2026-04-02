#!/usr/bin/env python3
"""WhiteboardQ Client - Desktop application for WhiteboardQ messaging system."""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(debug: bool = False) -> None:
    """Configure logging with file output.

    Args:
        debug: If True, log DEBUG level for whiteboardq_client.* modules.
               If False, log WARNING level only (production default).
    """
    # Log to AppData/WhiteboardQ/logs/client.log
    log_dir = Path.home() / "AppData" / "Roaming" / "WhiteboardQ" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "client.log"

    # Format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Root logger - WARNING to suppress noisy third-party libraries
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    root_logger.handlers.clear()

    # Our modules get more verbose logging when debug is enabled
    app_logger = logging.getLogger("whiteboardq_client")
    app_logger.setLevel(logging.DEBUG if debug else logging.WARNING)

    # File handler with rotation (2MB max, keep 2 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (only in debug mode)
    if debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if debug:
        logging.getLogger("whiteboardq_client").info(f"Debug logging enabled: {log_file}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="WhiteboardQ Client")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (verbose output for troubleshooting)",
    )
    args = parser.parse_args()

    setup_logging(debug=args.debug)

    # Use absolute import for PyInstaller compatibility
    from whiteboardq_client.app import run_app
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
