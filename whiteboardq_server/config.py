"""Server configuration from environment variables."""

import os
from pathlib import Path


def _default_data_dir() -> str:
    """Get default data directory: always %ProgramData%\\WhiteboardQ."""
    program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    return str(Path(program_data) / "WhiteboardQ")


class Config:
    """Server configuration with environment variable overrides.

    Data paths default to %ProgramData%\\WhiteboardQ\\ in both dev and production:
        ├── whiteboardq.db      (SQLite database)
        ├── config.json         (server configuration)
        ├── logs/server.log     (log files)
        └── certs/              (TLS certificates)
    """

    DATA_DIR: Path = Path(os.getenv("WHITEBOARD_DATA_DIR", _default_data_dir()))
    DB_PATH: Path = Path(os.getenv("WHITEBOARD_DB", str(Path(_default_data_dir()) / "whiteboardq.db")))
    HOST: str = os.getenv("WHITEBOARD_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WHITEBOARD_PORT", "5000"))

    # TLS settings - certs stored in DATA_DIR/certs/
    TLS_ENABLED: bool = os.getenv("WHITEBOARD_TLS", "1").lower() in ("1", "true", "yes")
    CERT_FILE: Path = Path(os.getenv("WHITEBOARD_CERT", str(Path(_default_data_dir()) / "certs" / "cert.pem")))
    KEY_FILE: Path = Path(os.getenv("WHITEBOARD_KEY", str(Path(_default_data_dir()) / "certs" / "key.pem")))
    CERT_HOSTNAME: str = os.getenv("WHITEBOARD_CERT_HOSTNAME", "localhost")

    # Default thresholds (can be overridden in DB)
    YELLOW_MINUTES: int = 10
    RED_MINUTES: int = 20
    OVERDUE_MINUTES: int = 30



config = Config()
