"""Settings dialog for server connection and display preferences."""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QCheckBox, QComboBox,
    QGroupBox, QLabel, QInputDialog
)

from ..config import ClientConfig
from ..discovery import discover_servers, test_connection
from ..theme import Theme, THEMES

# Registry helpers for Windows auto-start
if sys.platform == "win32":
    import winreg

    _REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    _REG_VALUE = "WhiteboardQ"

    def _get_auto_start() -> bool:
        """Check if auto-start is enabled in registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, _REG_VALUE)
                return True
        except FileNotFoundError:
            return False
        except OSError:
            return False

    def _set_auto_start(enabled: bool, exe_path: str = None) -> None:
        """Enable or disable auto-start in registry."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    if exe_path is None:
                        exe_path = sys.executable
                    winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(key, _REG_VALUE)
                    except FileNotFoundError:
                        pass  # Already deleted
        except OSError:
            pass  # Silently fail if can't access registry
else:
    # Non-Windows stubs
    def _get_auto_start() -> bool:
        return False

    def _set_auto_start(enabled: bool, exe_path: str = None) -> None:
        pass


class SettingsDialog(QDialog):
    """Settings dialog for client configuration.

    Note: Thresholds and sound selections are managed by the server.
    Only "Mute all sounds" is a local client preference.
    """

    def __init__(self, config: ClientConfig, theme: Theme, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self._setup_ui()
        self._load_values()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setModal(True)
        self._restore_geometry()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Connection settings
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)

        # Station name
        station_row = QHBoxLayout()
        self.station_input = QLineEdit()
        self.station_input.setPlaceholderText("e.g., Front-Desk")
        station_row.addWidget(self.station_input)

        self.auto_detect_btn = QPushButton("Auto-detect")
        self.auto_detect_btn.setMinimumWidth(80)
        self.auto_detect_btn.clicked.connect(self._auto_detect_station)
        station_row.addWidget(self.auto_detect_btn)

        conn_layout.addRow("Station Name:", station_row)

        # Server host and port
        server_row = QHBoxLayout()
        self.server_host_input = QLineEdit()
        self.server_host_input.setPlaceholderText("192.168.1.100")
        self.server_host_input.textChanged.connect(self._clear_status)
        server_row.addWidget(self.server_host_input)

        port_label = QLabel("Port:")
        server_row.addWidget(port_label)

        self.server_port_input = QLineEdit()
        self.server_port_input.setPlaceholderText("5000")
        self.server_port_input.setMaximumWidth(70)
        self.server_port_input.textChanged.connect(self._clear_status)
        server_row.addWidget(self.server_port_input)

        conn_layout.addRow("Server:", server_row)

        # Find Server and Test Connection buttons
        button_row = QHBoxLayout()

        self.find_server_btn = QPushButton("Find Server")
        self.find_server_btn.setMinimumWidth(100)
        self.find_server_btn.clicked.connect(self._find_server)
        button_row.addWidget(self.find_server_btn)

        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.setMinimumWidth(100)
        self.test_connection_btn.clicked.connect(self._test_connection)
        button_row.addWidget(self.test_connection_btn)

        self.connection_status_label = QLabel("")
        button_row.addWidget(self.connection_status_label)
        button_row.addStretch()

        conn_layout.addRow("", button_row)

        main_layout.addWidget(conn_group)

        # Appearance settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        appearance_layout.addRow("Theme:", self.theme_combo)

        main_layout.addWidget(appearance_group)

        # Behavior settings
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)

        self.always_on_top_cb = QCheckBox("Always on top")
        behavior_layout.addWidget(self.always_on_top_cb)

        self.auto_start_cb = QCheckBox("Start with Windows")
        behavior_layout.addWidget(self.auto_start_cb)

        self.confirm_delete_cb = QCheckBox("Confirm before delete")
        behavior_layout.addWidget(self.confirm_delete_cb)

        main_layout.addWidget(behavior_group)

        # Sound settings (only mute - other sound settings are server-managed)
        sound_group = QGroupBox("Sounds")
        sound_layout = QVBoxLayout(sound_group)

        self.sound_muted_cb = QCheckBox("Mute all sounds")
        sound_layout.addWidget(self.sound_muted_cb)

        # Info label
        info_label = QLabel("Sound selections are managed by the server administrator.")
        info_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        sound_layout.addWidget(info_label)

        main_layout.addWidget(sound_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.restore_defaults_btn = QPushButton("Restore Defaults")
        self.restore_defaults_btn.clicked.connect(self._restore_defaults)
        button_layout.addWidget(self.restore_defaults_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setProperty("accent", True)
        self.save_btn.clicked.connect(self._save)
        button_layout.addWidget(self.save_btn)

        main_layout.addLayout(button_layout)

    def _load_values(self) -> None:
        """Load current config values into UI."""
        self.station_input.setText(self.config.station_name)
        self.server_host_input.setText(self.config.server_host)
        self.server_port_input.setText(str(self.config.server_port))

        # Theme
        index = self.theme_combo.findData(self.config.theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # Behavior
        self.always_on_top_cb.setChecked(self.config.always_on_top)
        self.auto_start_cb.setChecked(_get_auto_start())  # Read from registry
        self.confirm_delete_cb.setChecked(self.config.confirm_delete)

        # Sounds (only mute is local)
        self.sound_muted_cb.setChecked(self.config.sound_muted)

    def _auto_detect_station(self) -> None:
        """Set station name to hostname."""
        self.station_input.setText(ClientConfig.get_default_station_name())

    def _clear_status(self) -> None:
        """Clear the connection status label."""
        self.connection_status_label.setText("")
        self.connection_status_label.setStyleSheet("")

    def _set_status(self, message: str, success: bool) -> None:
        """Set the connection status label with color."""
        color = "#28a745" if success else "#dc3545"  # Green or red
        prefix = "\u2713" if success else "\u2717"  # Checkmark or X
        self.connection_status_label.setText(f"{prefix} {message}")
        self.connection_status_label.setStyleSheet(f"color: {color};")

    def _find_server(self) -> None:
        """Discover servers on the LAN and populate fields."""
        # Disable button and show searching state
        self.find_server_btn.setEnabled(False)
        self.find_server_btn.setText("Searching...")
        self._clear_status()

        # Force UI update
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            servers = discover_servers(timeout=2.0)

            if not servers:
                self._set_status("No servers found", False)
            elif len(servers) == 1:
                # Single server found - populate directly
                server = servers[0]
                self.server_host_input.setText(server.host)
                self.server_port_input.setText(str(server.port))
                self._set_status(f"Found: {server.host}:{server.port}", True)
            else:
                # Multiple servers - show picker
                items = [f"{s.host}:{s.port}" for s in servers]
                choice, ok = QInputDialog.getItem(
                    self, "Select Server",
                    "Multiple servers found. Select one:",
                    items, 0, False
                )
                if ok and choice:
                    # Parse selection
                    host, port_str = choice.rsplit(":", 1)
                    self.server_host_input.setText(host)
                    self.server_port_input.setText(port_str)
                    self._set_status(f"Selected: {choice}", True)
        finally:
            # Restore button
            self.find_server_btn.setEnabled(True)
            self.find_server_btn.setText("Find Server")

    def _test_connection(self) -> None:
        """Test TCP connection to the configured server."""
        host = self.server_host_input.text().strip()
        port_str = self.server_port_input.text().strip()

        # Validate inputs
        if not host:
            self._set_status("Enter a server address", False)
            return

        try:
            port = int(port_str) if port_str else 5000
        except ValueError:
            self._set_status(f"Invalid port: {port_str}", False)
            return

        # Disable button and show testing state
        self.test_connection_btn.setEnabled(False)
        self.test_connection_btn.setText("Testing...")
        self._clear_status()

        # Force UI update
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            success, message = test_connection(host, port, timeout=3.0)
            self._set_status(message, success)
        finally:
            # Restore button
            self.test_connection_btn.setEnabled(True)
            self.test_connection_btn.setText("Test Connection")

    def _restore_defaults(self) -> None:
        """Restore all settings to default values."""
        defaults = ClientConfig.get_restorable_defaults()

        # Connection
        self.station_input.setText(defaults["station_name"])
        self.server_host_input.setText(defaults["server_host"])
        self.server_port_input.setText(str(defaults["server_port"]))

        # Theme
        index = self.theme_combo.findData(defaults["theme"])
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # Behavior
        self.always_on_top_cb.setChecked(defaults["always_on_top"])
        self.auto_start_cb.setChecked(False)  # Default is off
        self.confirm_delete_cb.setChecked(defaults["confirm_delete"])

        # Sounds (only mute is local)
        self.sound_muted_cb.setChecked(defaults["sound_muted"])

    def _save(self) -> None:
        """Save settings and close."""
        self.config.station_name = self.station_input.text().strip()
        self.config.server_host = self.server_host_input.text().strip()
        try:
            self.config.server_port = int(self.server_port_input.text().strip())
        except ValueError:
            self.config.server_port = 5000
        self.config.theme = self.theme_combo.currentData()
        self.config.always_on_top = self.always_on_top_cb.isChecked()
        _set_auto_start(self.auto_start_cb.isChecked())  # Write to registry
        self.config.confirm_delete = self.confirm_delete_cb.isChecked()
        self.config.sound_muted = self.sound_muted_cb.isChecked()

        self._save_geometry()
        self.config.save()
        self.accept()

    def reject(self) -> None:
        """Handle cancel/close."""
        self._save_geometry()
        self.config.save()
        super().reject()

    def _save_geometry(self) -> None:
        """Save window position to config."""
        geo = self.geometry()
        # Only save position - size is determined by content
        self.config.settings_window_geometry = [geo.x(), geo.y(), 0, 0]

    def _restore_geometry(self) -> None:
        """Restore window geometry from config."""
        geo = self.config.settings_window_geometry
        if geo and len(geo) == 4:
            # Only restore position, not size - let dialog size to content
            self.move(geo[0], geo[1])
        # Let the dialog size itself based on content
        self.adjustSize()

    def get_config(self) -> ClientConfig:
        """Get the (possibly modified) config."""
        return self.config
