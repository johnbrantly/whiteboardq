"""Application lifecycle — creates QApplication, event loop, WebSocket client, and main window."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .config import ClientConfig
from .theme import THEMES, get_stylesheet
from .network.websocket_client import WebSocketClient
from .ui.main_window import MainWindow
from .ui.welcome_dialog import WelcomeDialog
from .ui.setup_dialog import SetupDialog
from .sounds import SoundManager


class WhiteboardQApp:
    """Main application class managing lifecycle and components."""

    def __init__(self):
        self.app: Optional[QApplication] = None
        self.loop: Optional[QEventLoop] = None
        self.config: Optional[ClientConfig] = None
        self.ws_client: Optional[WebSocketClient] = None
        self.main_window: Optional[MainWindow] = None
        self.sound_manager: Optional[SoundManager] = None
        self._reconnect_task: Optional[asyncio.Task] = None

    def _get_icon_path(self) -> Path:
        """Get path to application icon, handling PyInstaller frozen mode."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable - bundled in whiteboardq_client/resources
            return Path(sys._MEIPASS) / "whiteboardq_client" / "resources" / "icon.png"
        else:
            return Path(__file__).parent / "resources" / "icon.png"

    def run(self) -> int:
        """Run the application."""
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("WhiteboardQ")
        self.app.setOrganizationName("WhiteboardQ")

        # Set application icon (applies to all windows)
        icon_path = self._get_icon_path()
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))

        # Load configuration
        self.config = ClientConfig.load()

        # Setup async event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        # Create components
        self._create_components()

        # Apply initial stylesheet
        self._apply_stylesheet()

        # Show welcome dialog on first run
        if not self.config.disclaimer_acknowledged:
            self._show_welcome_dialog()

        # Show setup dialog if not completed
        if not self.config.setup_completed:
            self._show_setup_dialog()

        # Show window
        self.main_window.show()

        # Start WebSocket connection
        self._start_connection()

        # Run event loop
        with self.loop:
            return self.loop.run_forever()

    def _create_components(self) -> None:
        """Create all application components."""
        # Sound manager
        self.sound_manager = SoundManager()
        self._apply_sound_settings()

        # WebSocket client - use effective station name (hostname if not set)
        self.ws_client = WebSocketClient(
            server_url=self.config.server_url,
            station_name=self.config.get_effective_station_name(),
            verify_ssl=self.config.verify_ssl
        )

        # Main window
        self.main_window = MainWindow(self.config, self.ws_client)
        self.main_window.set_sound_manager(self.sound_manager)

        # Connect window close to app quit
        self.main_window.destroyed.connect(self._on_window_closed)

    def _apply_stylesheet(self) -> None:
        """Apply the global stylesheet."""
        theme = THEMES[self.config.theme]
        self.app.setStyleSheet(get_stylesheet(theme))

    def _show_welcome_dialog(self) -> None:
        """Show the first-run welcome/disclaimer dialog."""
        theme = THEMES[self.config.theme]
        dialog = WelcomeDialog(theme)
        dialog.exec()

        if dialog.dont_show_again:
            self.config.disclaimer_acknowledged = True
            self.config.save()

    def _show_setup_dialog(self) -> None:
        """Show the first-run setup dialog for server configuration."""
        theme = THEMES[self.config.theme]
        dialog = SetupDialog(self.config, theme)
        dialog.exec()

        # Reload config in case setup dialog saved changes
        self.config = ClientConfig.load()

        # Update WebSocket client with new config
        self.ws_client.update_config(
            server_url=self.config.server_url,
            station_name=self.config.get_effective_station_name(),
            verify_ssl=self.config.verify_ssl
        )

    def _apply_sound_settings(self) -> None:
        """Apply sound configuration to the sound manager."""
        self.sound_manager.set_muted(self.config.sound_muted)
        self.sound_manager.set_sound_file("new_message", self.config.sound_new_message)
        self.sound_manager.set_sound_file("yellow", self.config.sound_yellow)
        self.sound_manager.set_sound_file("red", self.config.sound_red)
        self.sound_manager.set_sound_file("overdue", self.config.sound_overdue)

    def _start_connection(self) -> None:
        """Start the WebSocket connection."""
        self._reconnect_task = self.loop.create_task(self._connection_loop())

    async def _connection_loop(self) -> None:
        """Manage WebSocket connection with auto-reconnect."""
        while True:
            try:
                await self.ws_client.connect_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection error: {e}")

            # Wait before reconnecting (can be interrupted by reconnect())
            await self.ws_client.wait_before_reconnect(3.0)

    def _on_window_closed(self) -> None:
        """Handle main window closed."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
        self.loop.stop()


def run_app() -> int:
    """Entry point for running the application."""
    app = WhiteboardQApp()
    return app.run()
