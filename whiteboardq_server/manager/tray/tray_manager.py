"""System tray icon management for WhiteboardQ Server Manager."""

import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

from .icons import get_icon_path, TrayState
from .server_controller import ServerController, ServerState


class TrayManager(QObject):
    """Manages the system tray icon and its interactions.

    Provides a system tray presence for the WhiteboardQ Server Manager
    with status indication, context menu, and window activation.

    Signals:
        show_window_requested: Emitted when user wants to see the main window
        quit_requested: Emitted when user wants to exit the application
    """

    show_window_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        log_dir: Path,
        auto_start_server: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self._log_dir = log_dir
        self._main_window = None

        # Create server controller
        self._controller = ServerController(self)
        self._controller.status_changed.connect(self._on_status_changed)
        self._controller.error_occurred.connect(self._on_error)

        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.activated.connect(self._on_tray_activated)

        # Set initial icon (stopped state)
        self._set_icon(TrayState.STOPPED)
        self._update_tooltip(ServerState.STOPPED, 0, 0)

        # Create context menu
        self._create_context_menu()

        # Show tray icon
        self._tray_icon.show()

        # Auto-start server if requested
        if auto_start_server:
            # Delay slightly to ensure UI is ready
            from PySide6.QtCore import QTimer
            QTimer.singleShot(500, self._controller.start)

        # Start monitoring
        self._controller.start_monitoring()

    @property
    def controller(self) -> ServerController:
        """Get the server controller."""
        return self._controller

    def set_main_window(self, window):
        """Set the main window reference for showing/hiding."""
        self._main_window = window

    def _create_context_menu(self):
        """Create the system tray context menu."""
        menu = QMenu()

        # Open Manager
        self._open_action = QAction("Open Manager", self)
        self._open_action.triggered.connect(self._on_open_manager)
        menu.addAction(self._open_action)

        menu.addSeparator()

        # Start Server
        self._start_action = QAction("Start Server", self)
        self._start_action.triggered.connect(self._controller.start)
        menu.addAction(self._start_action)

        # Stop Server
        self._stop_action = QAction("Stop Server", self)
        self._stop_action.triggered.connect(self._controller.stop)
        self._stop_action.setEnabled(False)
        menu.addAction(self._stop_action)

        menu.addSeparator()

        # View Logs
        self._logs_action = QAction("View Logs", self)
        self._logs_action.triggered.connect(self._on_view_logs)
        menu.addAction(self._logs_action)

        menu.addSeparator()

        # Exit
        self._exit_action = QAction("Exit", self)
        self._exit_action.triggered.connect(self._on_exit)
        menu.addAction(self._exit_action)

        self._tray_icon.setContextMenu(menu)

    def _set_icon(self, state: TrayState):
        """Update the tray icon based on state."""
        icon_path = get_icon_path(state)
        if icon_path and icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback to application icon
            app = QApplication.instance()
            if app:
                self._tray_icon.setIcon(app.windowIcon())

    def _update_tooltip(self, state: ServerState, clients: int, uptime: int):
        """Update the tooltip text based on state."""
        if state == ServerState.STOPPED:
            tooltip = "WhiteboardQ Server - Stopped"
        elif state == ServerState.STARTING:
            tooltip = "WhiteboardQ Server - Starting..."
        elif state == ServerState.STOPPING:
            tooltip = "WhiteboardQ Server - Stopping..."
        elif state == ServerState.RUNNING:
            if clients >= 0:
                client_text = f"{clients} client" if clients == 1 else f"{clients} clients"
                tooltip = f"WhiteboardQ Server - Running ({client_text})"
            else:
                tooltip = "WhiteboardQ Server - Running"
        else:
            tooltip = "WhiteboardQ Server"

        self._tray_icon.setToolTip(tooltip)

    def _on_status_changed(self, state: ServerState, clients: int, uptime: int):
        """Handle server status changes."""
        # Update icon
        if state == ServerState.STOPPED:
            self._set_icon(TrayState.STOPPED)
        elif state in (ServerState.STARTING, ServerState.STOPPING):
            self._set_icon(TrayState.STARTING)  # Yellow for transitional states
        elif state == ServerState.RUNNING:
            self._set_icon(TrayState.RUNNING)

        # Update tooltip
        self._update_tooltip(state, clients, uptime)

        # Update menu actions
        if state == ServerState.RUNNING:
            self._start_action.setEnabled(False)
            self._stop_action.setEnabled(True)
        elif state == ServerState.STOPPED:
            self._start_action.setEnabled(True)
            self._stop_action.setEnabled(False)
        else:
            # Transitional state - disable both
            self._start_action.setEnabled(False)
            self._stop_action.setEnabled(False)

    def _on_error(self, message: str):
        """Handle error from server controller."""
        self._tray_icon.showMessage(
            "WhiteboardQ Server",
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            5000,  # Show for 5 seconds
        )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation (click)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Left-click - show manager window
            self._on_open_manager()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double-click - also show manager window
            self._on_open_manager()

    def _on_open_manager(self):
        """Show the main manager window."""
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()
        else:
            self.show_window_requested.emit()

    def _on_view_logs(self):
        """Open the log file."""
        log_file = self._log_dir / "server.log"
        if log_file.exists():
            os.startfile(str(log_file))
        else:
            self._tray_icon.showMessage(
                "WhiteboardQ Server",
                f"No log file found at:\n{log_file}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _on_exit(self):
        """Handle exit request."""
        # Stop server if running
        if self._controller.is_running:
            self._controller.stop()

        # Stop monitoring
        self._controller.stop_monitoring()

        # Hide tray icon
        self._tray_icon.hide()

        # Emit quit signal
        self.quit_requested.emit()

    def cleanup(self):
        """Clean up resources before application exit."""
        self._controller.stop_monitoring()
        self._tray_icon.hide()
