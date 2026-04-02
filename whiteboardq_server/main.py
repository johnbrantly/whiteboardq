"""FastAPI application setup, TLS, logging, and CLI entry point."""

import argparse
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add project root to path for version import
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from version import get_version, get_full_version
from .config import config
from .database import db
from .discovery import DiscoveryResponder
from .routes import api, ws


def setup_logging(debug: bool = False) -> None:
    """Configure logging with file and console handlers."""
    # Determine log level
    level = logging.DEBUG if debug else logging.INFO

    # Create logs directory per spec: %ProgramData%\WhiteboardQ\logs\
    log_dir = config.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"

    # Format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (5MB max, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


# Check for debug mode from environment
_debug_mode = os.environ.get("WHITEBOARD_DEBUG", "").lower() in ("1", "true", "yes")

# Initial logging setup (may be reconfigured in main() with CLI args)
setup_logging(debug=_debug_mode)
logger = logging.getLogger(__name__)


def get_base_dir() -> Path:
    """Get base directory, handling PyInstaller frozen mode."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys._MEIPASS) / "whiteboardq_server"
    return Path(__file__).parent


# Paths
BASE_DIR = get_base_dir()
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    app.state.start_time = time.time()

    logger.info(f"Connecting to database: {config.DB_PATH}")
    await db.connect()
    await db.init_db()
    logger.info("Database initialized")

    # Start UDP discovery responder
    discovery_responder = DiscoveryResponder(port=config.PORT)
    discovery_responder.start()
    app.state.discovery_responder = discovery_responder

    yield

    # Shutdown
    logger.info("Server shutting down, notifying clients...")

    # Stop discovery responder
    if hasattr(app.state, "discovery_responder"):
        app.state.discovery_responder.stop()

    from .websocket_manager import manager
    await manager.broadcast({"type": "server_shutdown", "message": "Server is shutting down"})
    logger.info("Closing database connection")
    await db.close()


VERSION = get_version()
FULL_VERSION = get_full_version()
COPYRIGHT = "Copyright (c) 2026 John Brantly. Licensed under GPL v3.0."


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="WhiteboardQ Server",
        description=f"Real-time intra-office messaging queue. {COPYRIGHT}",
        version=VERSION,
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(api.router)
    app.include_router(ws.router)

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Setup templates
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

    @app.get("/")
    async def index(request: Request):
        """Serve the browser client."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/about")
    async def about():
        """Return version and copyright information."""
        return {
            "name": "WhiteboardQ Server",
            "version": VERSION,
            "description": "Real-time intra-office messaging queue",
            "copyright": COPYRIGHT,
        }

    return app


app = create_app()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="WhiteboardQ Server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"WhiteboardQ Server v{VERSION} - {COPYRIGHT}",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the database and exit",
    )
    parser.add_argument(
        "--host",
        default=config.HOST,
        help=f"Host to bind to (default: {config.HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.PORT,
        help=f"Port to bind to (default: {config.PORT})",
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Disable TLS (development only)",
    )
    parser.add_argument(
        "--generate-cert",
        action="store_true",
        help="Generate new self-signed certificate and exit",
    )
    parser.add_argument(
        "--cert-hostname",
        default=config.CERT_HOSTNAME,
        help=f"Hostname for certificate (default: {config.CERT_HOSTNAME})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (verbose output)",
    )

    args = parser.parse_args()

    # Reconfigure logging if --debug was passed
    debug_mode = args.debug or _debug_mode
    if args.debug and not _debug_mode:
        setup_logging(debug=True)
        logger.debug("Debug logging enabled via --debug flag")

    # Handle cert generation
    if args.generate_cert:
        from .certs import generate_self_signed_cert
        generate_self_signed_cert(
            hostname=args.cert_hostname,
            output_dir=config.CERT_FILE.parent,
        )
        sys.exit(0)

    if args.init_db:
        import asyncio

        async def init():
            await db.connect()
            await db.init_db()
            await db.close()
            logger.info(f"Database initialized at: {config.DB_PATH}")

        asyncio.run(init())
        sys.exit(0)

    # Determine TLS mode
    use_tls = config.TLS_ENABLED and not args.no_tls

    # Auto-generate cert if TLS enabled but certs don't exist
    if use_tls and (not config.CERT_FILE.exists() or not config.KEY_FILE.exists()):
        logger.info("TLS certificates not found. Generating self-signed certificate...")
        from .certs import generate_self_signed_cert
        generate_self_signed_cert(
            hostname=args.cert_hostname,
            output_dir=config.CERT_FILE.parent,
        )

    # Build uvicorn config
    uvicorn_config = {
        "host": args.host,
        "port": args.port,
        "access_log": debug_mode,  # Only log HTTP requests in debug mode
        "log_level": "debug" if debug_mode else "warning",
    }

    logger.info(f"WhiteboardQ Server {FULL_VERSION}")

    if use_tls:
        uvicorn_config["ssl_certfile"] = str(config.CERT_FILE)
        uvicorn_config["ssl_keyfile"] = str(config.KEY_FILE)
        logger.info(f"Starting server with TLS on https://{args.host}:{args.port}")
    else:
        logger.warning(f"Starting server WITHOUT TLS on http://{args.host}:{args.port}")
        logger.warning("Use --no-tls only for development!")

    # Run the server
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - pass app directly
        uvicorn.run(app, **uvicorn_config)
    else:
        # Development mode - use string import for reload support
        uvicorn.run("whiteboardq_server.main:app", reload=False, **uvicorn_config)


if __name__ == "__main__":
    main()
