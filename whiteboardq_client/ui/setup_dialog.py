"""First-run setup dialog for server configuration."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QMessageBox,
)

from ..config import ClientConfig
from ..discovery import discover_servers, test_connection, DiscoveredServer
from ..theme import Theme


class SetupDialog(QDialog):
    """First-run setup dialog for configuring server connection."""

    def __init__(self, config: ClientConfig, theme: Theme, parent=None):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self.discovered_servers: list[DiscoveredServer] = []
        self._setup_ui()

        # Auto-start discovery after dialog is shown
        QTimer.singleShot(100, self._start_discovery)

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle("WhiteboardQ Setup")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Welcome to WhiteboardQ")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.text_primary};
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Let's connect to your server")
        subtitle.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Server selection group
        server_group = QGroupBox("Server")
        server_layout = QVBoxLayout(server_group)

        # Status label (for discovery progress)
        self.status_label = QLabel("Searching for servers...")
        self.status_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-style: italic;")
        server_layout.addWidget(self.status_label)

        # Search again button
        self.retry_btn = QPushButton("Search Again")
        self.retry_btn.setMaximumWidth(120)
        self.retry_btn.clicked.connect(self._start_discovery)
        self.retry_btn.setVisible(False)
        server_layout.addWidget(self.retry_btn)

        # Server address fields (always visible)
        address_layout = QHBoxLayout()

        server_label = QLabel("Server:")
        address_layout.addWidget(server_label)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("IP address or hostname")
        self.host_input.textChanged.connect(self._on_input_changed)
        address_layout.addWidget(self.host_input, 3)

        port_label = QLabel("Port:")
        address_layout.addWidget(port_label)

        self.port_input = QLineEdit("5000")
        self.port_input.setMaximumWidth(70)
        self.port_input.textChanged.connect(self._on_input_changed)
        address_layout.addWidget(self.port_input)

        server_layout.addLayout(address_layout)

        # Hint for auto-detected server
        self.server_hint = QLabel("Auto-detected via network discovery. You can change it if needed.")
        self.server_hint.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px;")
        self.server_hint.setWordWrap(True)
        self.server_hint.setVisible(False)
        server_layout.addWidget(self.server_hint)

        layout.addWidget(server_group)

        # Station name group
        station_group = QGroupBox("Station Name")
        station_layout = QVBoxLayout(station_group)

        self.station_input = QLineEdit()
        self.station_input.setText(ClientConfig.get_default_station_name())
        station_layout.addWidget(self.station_input)

        station_hint = QLabel("Auto-detected from computer name. You can change it if needed.")
        station_hint.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px;")
        station_hint.setWordWrap(True)
        station_layout.addWidget(station_hint)

        layout.addWidget(station_group)

        # Connection status
        self.connection_status = QLabel("")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_status)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.setProperty("accent", True)
        self.connect_btn.clicked.connect(self._on_connect)
        button_layout.addWidget(self.connect_btn)

        layout.addLayout(button_layout)

    def _start_discovery(self) -> None:
        """Start server discovery."""
        self.status_label.setText("Searching for servers...")
        self.status_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-style: italic;")
        self.status_label.setVisible(True)
        self.server_hint.setVisible(False)
        self.retry_btn.setVisible(False)

        # Force UI update
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        # Run discovery
        self.discovered_servers = discover_servers(timeout=2.0)

        if len(self.discovered_servers) == 1:
            # Normal case - exactly one server found
            server = self.discovered_servers[0]
            self.status_label.setText(f"\u2713 Server found: {server.host}:{server.port}")
            self.status_label.setStyleSheet(f"color: {self.theme.success}; font-style: normal;")

            # Populate fields
            self.host_input.setText(server.host)
            self.port_input.setText(str(server.port))
            self.server_hint.setVisible(True)

        elif len(self.discovered_servers) > 1:
            # Multiple servers - this is a problem!
            server_list = "\n".join(f"  • {s.host}:{s.port}" for s in self.discovered_servers)
            QMessageBox.warning(
                self,
                "Multiple Servers Detected",
                f"Found {len(self.discovered_servers)} WhiteboardQ servers on the network:\n\n"
                f"{server_list}\n\n"
                "There should only be one server running. Having multiple servers "
                "will cause synchronization issues.\n\n"
                "Please contact your IT administrator to resolve this immediately.\n\n"
                "The first server has been selected, but you can manually enter "
                "a different address if needed."
            )

            # Still populate with first server so user isn't blocked
            server = self.discovered_servers[0]
            self.status_label.setText("\u2717 Multiple servers found (see warning)")
            self.status_label.setStyleSheet(f"color: {self.theme.red}; font-style: normal;")

            self.host_input.setText(server.host)
            self.port_input.setText(str(server.port))
            self.server_hint.setVisible(False)

        else:
            self.status_label.setText("No servers found. Enter the server address manually:")
            self.status_label.setStyleSheet(f"color: {self.theme.yellow}; font-style: normal;")
            self.server_hint.setVisible(False)
            self.host_input.setFocus()

        self.retry_btn.setVisible(True)
        self._update_connect_button()

    def _on_input_changed(self) -> None:
        """Handle input field changes."""
        self._clear_status()
        self._update_connect_button()

    def _update_connect_button(self) -> None:
        """Enable/disable connect button based on input."""
        has_host = bool(self.host_input.text().strip())
        has_station = bool(self.station_input.text().strip())
        self.connect_btn.setEnabled(has_host and has_station)

    def _clear_status(self) -> None:
        """Clear connection status."""
        self.connection_status.setText("")

    def _set_status(self, message: str, is_success: bool) -> None:
        """Set connection status message."""
        color = self.theme.success if is_success else self.theme.red
        prefix = "\u2713" if is_success else "\u2717"
        self.connection_status.setText(f"{prefix} {message}")
        self.connection_status.setStyleSheet(f"color: {color};")

    def _on_connect(self) -> None:
        """Handle connect button click."""
        host = self.host_input.text().strip()
        station = self.station_input.text().strip()

        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 5000

        if not host:
            self._set_status("Please enter a server address", False)
            return

        if not station:
            self._set_status("Please enter a station name", False)
            return

        # Disable button and show testing state
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Testing...")
        self._clear_status()

        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        # Test connection
        success, message = test_connection(host, port, timeout=3.0)

        if success:
            # Save config and close
            self.config.server_host = host
            self.config.server_port = port
            self.config.station_name = station
            self.config.setup_completed = True
            self.config.save()
            self.accept()
        else:
            self._set_status(message, False)
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
