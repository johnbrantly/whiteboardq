"""Main application window — message list, sidebar, chat bar, status bar."""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QMessageBox, QApplication, QLabel, QFrame
)

from version import get_version, get_full_version
from ..config import ClientConfig
from ..theme import Theme, THEMES, get_stylesheet
from ..network.websocket_client import WebSocketClient
from .message_list import MessageList
from .message_card import MessageCard, MessageState
from .control_sidebar import ControlSidebar
from .chat_bar import ChatBar
from .status_bar import StatusBar
from .settings_dialog import SettingsDialog
from .delete_dialog import DeleteDialog
from .undo_toast import UndoToast


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: ClientConfig, ws_client: WebSocketClient):
        super().__init__()
        self.config = config
        self.ws_client = ws_client
        self.theme = THEMES[config.theme]
        self._pending_delete_data: Optional[dict] = None
        self._setup_ui()
        self._connect_signals()
        self._apply_config()

    def _setup_ui(self) -> None:
        """Build the main window UI."""
        self.setWindowTitle(f"WhiteboardQ v{get_version()}")
        self.setMinimumSize(100, 100)
        self._restore_geometry()

        # Menu bar
        self._setup_menu()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Status bar at top
        self.status_bar = StatusBar(self.theme)
        main_layout.addWidget(self.status_bar)

        # Content area (message list + sidebar)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Message list (main area)
        self.message_list = MessageList(self.theme)
        content_layout.addWidget(self.message_list, 1)

        # Control sidebar
        self.sidebar = ControlSidebar(self.theme)
        content_layout.addWidget(self.sidebar)

        main_layout.addLayout(content_layout, 1)

        # Undo toast (floating over message list)
        self.undo_toast = UndoToast(self.theme, self.message_list)

        # Chat bar at bottom
        self.chat_bar = ChatBar(self.theme)
        main_layout.addWidget(self.chat_bar)


        self._apply_theme()

    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        settings_action = file_menu.addAction("&Settings...")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        wipe_all_action = tools_menu.addAction("&Wipe All Messages...")
        wipe_all_action.triggered.connect(self._wipe_all_messages)

        restore_wipe_action = tools_menu.addAction("&Restore Last Wipe...")
        restore_wipe_action.triggered.connect(self._restore_last_wipe)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = help_menu.addAction("&About WhiteboardQ")
        about_action.triggered.connect(self._show_about)

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About WhiteboardQ",
            f"<h3>WhiteboardQ — Real-time message queue system</h3>"
            f"<p>Version {get_version()}</p>"
            f"<p><small>Build: {get_full_version()}</small></p>"
            f"<p>Copyright (c) 2026 John Brantly<br>"
            f"Licensed under the GNU General Public License v3.0<br>"
            f"See LICENSE file for details.</p>"
        )

    def _connect_signals(self) -> None:
        """Connect all signals."""
        # WebSocket signals
        self.ws_client.server_connected.connect(self._on_connected)
        self.ws_client.server_disconnected.connect(self._on_disconnected)
        self.ws_client.connection_error.connect(self._on_connection_error)
        self.ws_client.messages_loaded.connect(self._on_messages_loaded)
        self.ws_client.message_created.connect(self._on_message_created)
        self.ws_client.message_updated.connect(self._on_message_updated)
        self.ws_client.message_deleted.connect(self._on_message_deleted)
        self.ws_client.message_restored.connect(self._on_message_restored)
        self.ws_client.thresholds_received.connect(self._on_thresholds_received)

        # Message list signals
        self.message_list.selection_changed.connect(self._on_selection_changed)
        self.message_list.delete_requested.connect(self._on_delete_requested)
        self.message_list.state_changed.connect(self._on_message_state_changed)

        # Sidebar signals
        self.sidebar.move_top_clicked.connect(self._on_move_top)
        self.sidebar.move_up_clicked.connect(self._on_move_up)
        self.sidebar.move_down_clicked.connect(self._on_move_down)
        self.sidebar.delete_clicked.connect(self._on_delete_clicked)
        self.sidebar.restore_clicked.connect(self._on_restore_clicked)

        # Chat bar signals
        self.chat_bar.message_submitted.connect(self._on_message_submit)

        # Undo toast signals
        self.undo_toast.undo_clicked.connect(self._on_undo_clicked)
        self.undo_toast.dismissed.connect(self._on_undo_dismissed)

    def _apply_config(self) -> None:
        """Apply configuration settings."""
        # Always on top
        self._update_always_on_top()

        # Station name
        self.status_bar.set_station_name(self.config.station_name)

        # Apply thresholds from config
        self._apply_thresholds()

        # Disable input until connected
        self.chat_bar.set_enabled(False)

    def _apply_thresholds(self) -> None:
        """Apply threshold settings to UI components."""
        yellow = self.config.yellow_threshold_minutes
        red = self.config.red_threshold_minutes
        overdue = self.config.overdue_threshold_minutes
        self.status_bar.set_thresholds(yellow, red, overdue)
        self.message_list.set_thresholds(yellow, red, overdue)

    def _apply_theme(self) -> None:
        """Apply theme to all widgets."""
        self.setStyleSheet(get_stylesheet(self.theme))
        self.status_bar.set_theme(self.theme)
        self.message_list.set_theme(self.theme)
        self.sidebar.set_theme(self.theme)
        self.chat_bar.set_theme(self.theme)
        self.undo_toast.set_theme(self.theme)


    def _update_always_on_top(self) -> None:
        """Update always-on-top window flag (only safe at startup)."""
        if self.config.always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    def _restart_app(self) -> None:
        """Restart the application."""
        import sys
        import subprocess
        self._save_geometry()
        self.ws_client.disconnect()
        # Start new instance
        subprocess.Popen([sys.executable, "-m", "whiteboardq_client"])
        # Exit current instance
        QApplication.quit()

    def _wipe_all_messages(self) -> None:
        """Wipe all messages after confirmation."""
        reply = QMessageBox.warning(
            self,
            "Wipe All Messages",
            "Are you sure you want to delete ALL messages?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ws_client.wipe_all()

    def _restore_last_wipe(self) -> None:
        """Restore all messages from the last wipe after confirmation."""
        reply = QMessageBox.question(
            self,
            "Restore Last Wipe",
            "This will restore all messages that were deleted in the last 'Wipe All'.\n\n"
            "Any messages currently on the board will remain.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ws_client.restore_wipe()

    # Menu actions

    def _show_settings(self) -> None:
        """Show settings dialog."""
        old_always_on_top = self.config.always_on_top
        old_server_url = self.config.server_url
        old_station_name = self.config.station_name
        old_verify_ssl = self.config.verify_ssl

        dialog = SettingsDialog(self.config, self.theme, self)
        if dialog.exec():
            # Theme changed?
            if self.config.theme != self.theme.name:
                self.theme = THEMES[self.config.theme]
                self._apply_theme()
                # Update message cards with new theme
                self.message_list.set_theme(self.theme)

            # Always on top changed? Requires restart
            if self.config.always_on_top != old_always_on_top:
                reply = QMessageBox.question(
                    self,
                    "Restart Required",
                    "The 'Always on top' setting requires a restart to take effect.\n\nRestart now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._restart_app()

            # Station name changed?
            self.status_bar.set_station_name(self.config.station_name)

            # Thresholds changed?
            self._apply_thresholds()

            # Sound settings changed?
            self._apply_sound_settings()

            # Connection settings changed? Update client and reconnect
            connection_changed = (
                self.config.server_url != old_server_url or
                self.config.station_name != old_station_name or
                self.config.verify_ssl != old_verify_ssl
            )
            if connection_changed:
                self.ws_client.update_config(
                    self.config.server_url,
                    self.config.get_effective_station_name(),
                    self.config.verify_ssl
                )
                self.ws_client.reconnect()

    # WebSocket event handlers

    def _on_connected(self) -> None:
        """Handle WebSocket connected."""
        self.status_bar.set_connected(True)
        self.chat_bar.set_enabled(True)
        self.chat_bar.focus_input()

    def _on_disconnected(self) -> None:
        """Handle WebSocket disconnected - will auto-reconnect."""
        self.status_bar.set_connecting()
        self.chat_bar.set_enabled(False)

    def _on_connection_error(self, error: str) -> None:
        """Handle WebSocket connection error - will auto-reconnect."""
        self.status_bar.set_error(error)
        self.chat_bar.set_enabled(False)

    def _on_messages_loaded(self, messages: list) -> None:
        """Handle initial message load."""
        self.message_list.clear()
        for msg in messages:
            self._add_message_to_list(msg)

    def _on_message_created(self, message: dict) -> None:
        """Handle new message created."""
        self._add_message_to_list(message)
        # Emit sound if enabled
        self._play_sound("new_message")

    def _on_message_updated(self, message: dict) -> None:
        """Handle message updated (position change)."""
        self.message_list.update_message(message)

    def _on_message_deleted(self, message_id: str) -> None:
        """Handle message deleted (by another client)."""
        self.message_list.remove_message(message_id)

    def _on_message_restored(self, message: dict) -> None:
        """Handle message restored - add back to bottom of list."""
        # Hide undo toast if showing
        if self.undo_toast.isVisible():
            self.undo_toast.hide_toast()
        # Clear pending delete data since it's been restored
        self._pending_delete_data = None
        # Add message back to list (will be added at bottom due to position)
        self._add_message_to_list(message)

    def _on_thresholds_received(self, config: dict) -> None:
        """Accept threshold/sound config from server, persist only if changed."""
        changed = False

        # Thresholds
        if self.config.yellow_threshold_minutes != config.get("yellow_threshold_minutes", 10):
            self.config.yellow_threshold_minutes = config.get("yellow_threshold_minutes", 10)
            changed = True
        if self.config.red_threshold_minutes != config.get("red_threshold_minutes", 20):
            self.config.red_threshold_minutes = config.get("red_threshold_minutes", 20)
            changed = True
        if self.config.overdue_threshold_minutes != config.get("overdue_threshold_minutes", 30):
            self.config.overdue_threshold_minutes = config.get("overdue_threshold_minutes", 30)
            changed = True

        # Sounds
        if self.config.sound_new_message != config.get("sound_new_message", ""):
            self.config.sound_new_message = config.get("sound_new_message", "")
            changed = True
        if self.config.sound_yellow != config.get("sound_yellow", "soft.wav"):
            self.config.sound_yellow = config.get("sound_yellow", "soft.wav")
            changed = True
        if self.config.sound_red != config.get("sound_red", "chimes.wav"):
            self.config.sound_red = config.get("sound_red", "chimes.wav")
            changed = True
        if self.config.sound_overdue != config.get("sound_overdue", "littletrumpet.wav"):
            self.config.sound_overdue = config.get("sound_overdue", "littletrumpet.wav")
            changed = True

        if changed:
            self.config.save()
            self._apply_thresholds()

    def _add_message_to_list(self, message: dict) -> None:
        """Add a message to the list."""
        created_at = datetime.fromisoformat(message["created_at"].replace("Z", "+00:00"))
        self.message_list.add_message(
            message_id=message["id"],
            content=message["content"],
            station_name=message["station_name"],
            created_at=created_at,
            position=message["position"],
            is_important=message.get("is_important", False)
        )

    # Selection handling

    def _on_selection_changed(self, message_id: Optional[str]) -> None:
        """Handle message selection change."""
        if message_id is None:
            self.sidebar.set_selection(None, False, False, False)
        else:
            card = self.message_list.get_card(message_id)
            if card:
                is_first = self.message_list.is_first(message_id)
                is_last = self.message_list.is_last(message_id)
                is_important = card.is_important
                self.sidebar.set_selection(message_id, is_first, is_last, is_important)

    def _on_message_state_changed(self, message_id: str, new_state: MessageState) -> None:
        """Handle message state change - play warning sounds."""
        if new_state == MessageState.YELLOW:
            self._play_sound("yellow")
        elif new_state == MessageState.RED:
            self._play_sound("red")
        elif new_state == MessageState.OVERDUE:
            self._play_sound("overdue")

    # Sidebar actions

    def _on_move_top(self) -> None:
        """Move selected message to top."""
        card = self.message_list.get_selected_card()
        if card:
            self.ws_client.move_message(card.message_id, "top")

    def _on_move_up(self) -> None:
        """Move selected message up."""
        card = self.message_list.get_selected_card()
        if card:
            self.ws_client.move_message(card.message_id, "up")

    def _on_move_down(self) -> None:
        """Move selected message down."""
        card = self.message_list.get_selected_card()
        if card:
            self.ws_client.move_message(card.message_id, "down")

    def _on_delete_clicked(self) -> None:
        """Handle delete button clicked."""
        card = self.message_list.get_selected_card()
        if card:
            self._request_delete(card)

    def _on_delete_requested(self, message_id: str) -> None:
        """Handle delete request from message list (e.g., keyboard shortcut)."""
        card = self.message_list.get_card(message_id)
        if card:
            self._request_delete(card)

    def _request_delete(self, card: MessageCard) -> None:
        """Request deletion of a message, possibly showing confirmation."""
        if self.config.confirm_delete:
            dialog = DeleteDialog(
                content=card.content,
                station_name=card.station_name,
                created_at=card.created_at,
                theme=self.theme,
                parent=self
            )
            if dialog.exec():
                if dialog.dont_ask_again():
                    self.config.confirm_delete = False
                    self.config.save()
                self._delete_message(card)
        else:
            self._delete_message(card)

    def _delete_message(self, card: MessageCard) -> None:
        """Delete a message and show undo toast."""
        # Store data for potential undo
        self._pending_delete_data = {
            "id": card.message_id,
            "content": card.content,
            "station_name": card.station_name,
            "created_at": card.created_at.isoformat()
        }

        # Send delete to server
        self.ws_client.delete_message(card.message_id)

        # Show undo toast
        self.undo_toast.show_toast(card.message_id)

        # Position toast at bottom of message list
        self._position_undo_toast()

    def _position_undo_toast(self) -> None:
        """Position the undo toast at the bottom of the message list."""
        list_rect = self.message_list.rect()
        toast_width = min(400, list_rect.width() - 40)
        toast_height = 50

        x = (list_rect.width() - toast_width) // 2
        y = list_rect.height() - toast_height - 20

        self.undo_toast.setFixedSize(toast_width, toast_height)
        self.undo_toast.move(x, y)

    def _on_restore_clicked(self) -> None:
        """Handle restore button clicked - restore last deleted message."""
        if not self._pending_delete_data:
            return

        msg_id = self._pending_delete_data.get("id")
        if not msg_id:
            return

        if self.config.confirm_delete:
            # Show confirmation dialog
            msg_content = self._pending_delete_data.get("content", "")
            msg_station = self._pending_delete_data.get("station_name", "")
            display_content = msg_content[:100] + "..." if len(msg_content) > 100 else msg_content

            reply = QMessageBox.question(
                self,
                "Restore Message?",
                f"Restore this message from {msg_station}?\n\n\"{display_content}\"",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.ws_client.restore_message(msg_id)
        # Hide toast if showing
        if self.undo_toast.isVisible():
            self.undo_toast.hide_toast()

    def _on_undo_clicked(self) -> None:
        """Handle undo button clicked."""
        message_id = self.undo_toast.get_deleted_message_id()
        if message_id:
            self.ws_client.restore_message(message_id)

    def _on_undo_dismissed(self) -> None:
        """Handle undo toast dismissed (timeout)."""
        # Don't clear pending data - keep it for sidebar restore button
        pass

    # Chat bar

    def _on_message_submit(self, content: str) -> None:
        """Handle message submission."""
        self.ws_client.create_message(content)

    # Sound

    def _play_sound(self, sound_type: str) -> None:
        """Play a sound if enabled."""
        if hasattr(self, '_sound_manager') and self._sound_manager:
            if sound_type == "new_message" and self.config.sound_new_message:
                self._sound_manager.play_new_message()
            elif sound_type == "yellow" and self.config.sound_yellow:
                self._sound_manager.play_yellow_warning()
            elif sound_type == "red" and self.config.sound_red:
                self._sound_manager.play_red_warning()
            elif sound_type == "overdue" and self.config.sound_overdue:
                self._sound_manager.play_overdue_alert()

    def set_sound_manager(self, sound_manager) -> None:
        """Set the sound manager for playing sounds."""
        self._sound_manager = sound_manager

    def _apply_sound_settings(self) -> None:
        """Apply current sound configuration to the sound manager."""
        if hasattr(self, '_sound_manager') and self._sound_manager:
            self._sound_manager.set_muted(self.config.sound_muted)
            self._sound_manager.set_sound_file("new_message", self.config.sound_new_message)
            self._sound_manager.set_sound_file("yellow", self.config.sound_yellow)
            self._sound_manager.set_sound_file("red", self.config.sound_red)
            self._sound_manager.set_sound_file("overdue", self.config.sound_overdue)

    # Events

    def resizeEvent(self, event) -> None:
        """Handle window resize."""
        super().resizeEvent(event)
        if self.undo_toast.isVisible():
            self._position_undo_toast()

    def closeEvent(self, event) -> None:
        """Handle window close."""
        # Save window geometry
        self._save_geometry()
        # Disconnect WebSocket
        self.ws_client.disconnect()
        event.accept()

    def _save_geometry(self) -> None:
        """Save window geometry to config."""
        geo = self.geometry()
        self.config.main_window_geometry = [geo.x(), geo.y(), geo.width(), geo.height()]
        self.config.save()

    def _restore_geometry(self) -> None:
        """Restore window geometry from config."""
        geo = self.config.main_window_geometry
        if geo and len(geo) == 4:
            self.setGeometry(geo[0], geo[1], geo[2], geo[3])
        else:
            self.resize(1024, 768)
