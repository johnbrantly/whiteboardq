"""Tray application module for WhiteboardQ Server Manager.

Provides system tray integration for the Front Desk deployment scenario.
"""

from .tray_manager import TrayManager
from .server_controller import ServerController
from .icons import get_icon_path, TrayState

__all__ = ["TrayManager", "ServerController", "get_icon_path", "TrayState"]
