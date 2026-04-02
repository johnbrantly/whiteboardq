"""Icon path resolution for tray application."""

import sys
from enum import Enum
from pathlib import Path


class TrayState(Enum):
    """Server state for tray icon display."""

    STOPPED = "red"
    STARTING = "yellow"
    STOPPING = "yellow"
    RUNNING = "green"


def get_icon_path(state: TrayState) -> Path:
    """Get path to tray icon for the given state.

    Args:
        state: The server state to get icon for

    Returns:
        Path to the appropriate .ico file
    """
    icon_name = f"tray_{state.value}.ico"

    if getattr(sys, "frozen", False):
        # Running as compiled exe - icons bundled in _MEIPASS
        base_path = Path(sys._MEIPASS) / "whiteboardq_server" / "resources"
    else:
        # Development mode - use server resources folder
        base_path = Path(__file__).parent.parent.parent / "resources"

    icon_path = base_path / icon_name

    # Fallback to client icon if tray icon not found
    if not icon_path.exists():
        if getattr(sys, "frozen", False):
            fallback = Path(sys._MEIPASS) / "whiteboardq_server" / "resources" / "icon.ico"
        else:
            fallback = Path(__file__).parent.parent.parent.parent / "whiteboardq_client" / "resources" / "icon.ico"
        if fallback.exists():
            return fallback

    return icon_path


def get_app_icon_path() -> Path:
    """Get path to main application icon.

    Returns:
        Path to the main application .ico file
    """
    if getattr(sys, "frozen", False):
        icon_path = Path(sys._MEIPASS) / "whiteboardq_server" / "resources" / "icon.ico"
    else:
        icon_path = Path(__file__).parent.parent.parent.parent / "whiteboardq_client" / "resources" / "icon.ico"

    return icon_path if icon_path.exists() else None
