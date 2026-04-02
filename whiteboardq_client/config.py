"""Client configuration dataclass with JSON persistence to %APPDATA%."""

import json
import socket
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ClientConfig:
    """Client configuration stored in AppData."""

    server_host: str = "localhost"
    server_port: int = 5000
    station_name: str = ""
    verify_ssl: bool = False  # Accept self-signed certificates
    disclaimer_acknowledged: bool = False  # PHI disclaimer shown
    setup_completed: bool = False  # First-run setup wizard completed
    theme: str = "light"
    always_on_top: bool = True
    confirm_delete: bool = True
    sound_muted: bool = False
    sound_new_message: str = ""
    sound_yellow: str = "soft.wav"
    sound_red: str = "chimes.wav"
    sound_overdue: str = "littletrumpet.wav"

    # Window geometry (x, y, width, height)
    main_window_geometry: list = None
    settings_window_geometry: list = None

    # Server config (received from server)
    yellow_threshold_minutes: int = 10
    red_threshold_minutes: int = 20
    overdue_threshold_minutes: int = 30

    @staticmethod
    def get_default_station_name() -> str:
        """Get default station name from hostname."""
        return socket.gethostname()

    @property
    def server_url(self) -> str:
        """Construct the full WebSocket URL from host and port."""
        return f"wss://{self.server_host}:{self.server_port}"

    @classmethod
    def get_restorable_defaults(cls) -> dict:
        """Get default values for user-restorable settings."""
        return {
            "server_host": "localhost",
            "server_port": 5000,
            "station_name": cls.get_default_station_name(),
            "theme": "light",
            "always_on_top": True,
            "confirm_delete": True,
            "sound_muted": False,
            "sound_new_message": "",
            "sound_yellow": "soft.wav",
            "sound_red": "chimes.wav",
            "sound_overdue": "littletrumpet.wav",
            "yellow_threshold_minutes": 10,
            "red_threshold_minutes": 20,
            "overdue_threshold_minutes": 30,
        }

    @staticmethod
    def config_dir() -> Path:
        """Get config directory path."""
        return Path.home() / "AppData" / "Roaming" / "WhiteboardQ"

    @staticmethod
    def config_path() -> Path:
        """Get config file path."""
        return ClientConfig.config_dir() / "settings.json"

    def save(self) -> None:
        """Save config to file atomically."""
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file, then rename (atomic on most filesystems)
        temp_path = path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(asdict(self), indent=2))
        temp_path.replace(path)

    @classmethod
    def load(cls) -> "ClientConfig":
        """Load config from file, or return defaults."""
        path = cls.config_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def get_effective_station_name(self) -> str:
        """Get station name, using hostname if not set."""
        return self.station_name or self.get_default_station_name()
