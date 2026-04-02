"""Server Manager main window - matches mockup design."""

import os
import sys
import ssl
import subprocess
import urllib.request
import json
from pathlib import Path

# Add project root to path for version import
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from version import get_version

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
    QGridLayout,
    QSizePolicy,
    QSpinBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap

from whiteboardq_server.manager.sounds import SoundManager

# pywin32 for service control (BackOffice mode)
try:
    import win32serviceutil
    import win32service
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


# Base stylesheet for light mode
LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F3F4F6;
    color: #1F2937;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel {
    background: transparent;
}

QLineEdit {
    background-color: white;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Consolas", monospace;
    font-size: 13px;
    color: #374151;
}

QLineEdit:focus {
    border-color: #3B82F6;
}

QLineEdit::placeholder {
    color: #9CA3AF;
}

QPushButton {
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton#start {
    background-color: #22C55E;
    color: white;
    border: none;
}

QPushButton#start:hover {
    background-color: #16A34A;
}

QPushButton#start:disabled {
    background-color: #D1D5DB;
    color: #9CA3AF;
}

QPushButton#stop {
    background-color: #EF4444;
    color: white;
    border: none;
}

QPushButton#stop:hover {
    background-color: #DC2626;
}

QPushButton#stop:disabled {
    background-color: #D1D5DB;
    color: #9CA3AF;
}

QPushButton#secondary {
    background-color: #F9FAFB;
    color: #374151;
    border: 1px solid #D1D5DB;
}

QPushButton#secondary:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
}
"""


class Card(QFrame):
    """A card container with rounded borders."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            Card {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(8)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1F2937;
        """)
        self.layout.addWidget(title_label)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def addLayout(self, layout):
        self.layout.addLayout(layout)


class StatusDot(QLabel):
    """A colored status dot indicator."""

    def __init__(self, color: str = "#9CA3AF", parent=None):
        super().__init__("●", parent)
        self.setFixedWidth(20)
        self.set_color(color)

    def set_color(self, color: str):
        self.setStyleSheet(f"color: {color}; font-size: 14px;")


class StatusWorker(QObject):
    """Background worker for checking server status without blocking UI."""

    finished = Signal(bool, bool, int, int)  # service_running, process_running, clients, uptime

    def __init__(self):
        super().__init__()
        self._server_process = None

    def set_server_process(self, proc):
        self._server_process = proc

    def run(self):
        """Check status in background thread."""
        service_running = self._check_service()
        process_running = self._check_process()
        clients = -1
        uptime = -1

        if service_running or process_running:
            clients, uptime = self._fetch_health()

        self.finished.emit(service_running, process_running, clients, uptime)

    def _check_service(self) -> bool:
        """Check if WhiteboardQ Windows service is running."""
        try:
            result = subprocess.run(
                ["sc", "query", "WhiteboardQServer"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return "RUNNING" in result.stdout
        except Exception:
            return False

    def _check_process(self) -> bool:
        """Check if WhiteboardQ server process is running."""
        if self._server_process and self._server_process.poll() is None:
            return True
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WhiteboardQ-Server.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            lines = result.stdout.strip().split("\n")
            return len(lines) > 1 and "WhiteboardQ-Server.exe" in result.stdout
        except Exception:
            return False

    def _fetch_health(self) -> tuple[int, int]:
        """Fetch health data from server. Returns (clients, uptime_seconds)."""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://localhost:5000/health"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req, timeout=2, context=ctx) as response:
                data = json.loads(response.read().decode())
                checks = data.get("checks", {})
                clients = checks.get("connected_clients", 0)
                uptime = data.get("uptime_seconds", 0)
                return clients, uptime
        except Exception:
            return -1, -1


class MainWindow(QMainWindow):
    """Server Manager main window."""

    def __init__(
        self,
        mode: str,
        db_file: Path,
        log_dir: Path,
        service_name: str = "WhiteBoardServer",
    ):
        """Initialize the main window.

        Args:
            mode: Either "frontdesk" (tray mode, subprocess control) or
                  "backoffice" (no tray, service control).
            db_file: Path to whiteboardq.db
            log_dir: Path to logs directory
            service_name: Windows service name (for backoffice mode)
        """
        super().__init__()
        self._mode = mode
        self.db_file = db_file
        self.log_dir = log_dir
        self.service_name = service_name

        self.setWindowTitle("WhiteboardQ Server Manager")
        self.setMinimumSize(765, 840)
        self.setStyleSheet(LIGHT_STYLESHEET)

        # Server process tracking
        self._server_process = None

        # Tray manager (set externally when in frontdesk mode)
        self._tray_manager = None

        # Background status worker
        self._status_thread = None
        self._status_worker = None
        self._status_check_pending = False

        # Force light mode palette
        self._set_light_palette()

        self._setup_ui()
        self._refresh_status()

        # Refresh server status every 5 seconds (uses background thread)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._start_status_check)
        self.status_timer.start(5000)

    def set_tray_manager(self, tray_manager):
        """Set the tray manager for frontdesk mode integration.

        When a tray manager is set, the ServerController's signals are
        connected to update the UI.
        """
        self._tray_manager = tray_manager

        # Connect ServerController signals to update our UI
        if tray_manager and tray_manager.controller:
            tray_manager.controller.status_changed.connect(self._on_controller_status_changed)
            tray_manager.controller.error_occurred.connect(self._on_controller_error)

    def _on_controller_status_changed(self, state, clients, uptime):
        """Handle status change from ServerController (tray mode)."""
        from ..tray.server_controller import ServerState

        if state == ServerState.RUNNING:
            self.service_status_dot.set_color("#22C55E")  # Green
            self.service_status_text.setText("Running (exe)")
            self.service_status_text.setStyleSheet("font-weight: 500; color: #166534;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.clients_value.setText(str(clients) if clients >= 0 else "—")
            self.uptime_value.setText(self._format_uptime(uptime) if uptime >= 0 else "—")
        elif state == ServerState.STOPPED:
            self.service_status_dot.set_color("#9CA3AF")  # Gray
            self.service_status_text.setText("Stopped")
            self.service_status_text.setStyleSheet("font-weight: 500; color: #6B7280;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.clients_value.setText("—")
            self.uptime_value.setText("—")
        elif state in (ServerState.STARTING, ServerState.STOPPING):
            self.service_status_dot.set_color("#F59E0B")  # Yellow/orange
            text = "Starting..." if state == ServerState.STARTING else "Stopping..."
            self.service_status_text.setText(text)
            self.service_status_text.setStyleSheet("font-weight: 500; color: #92400E;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def _on_controller_error(self, message):
        """Handle error from ServerController (tray mode)."""
        QMessageBox.warning(self, "Server Error", message)

    def closeEvent(self, event):
        """Handle window close event.

        In frontdesk mode, hide the window instead of closing (tray remains).
        In backoffice mode, close normally (exit app).
        """
        if self._mode == "frontdesk":
            # FrontDesk mode - hide window instead of closing
            event.ignore()
            self.hide()
        else:
            # BackOffice mode - close normally
            event.accept()

    def _set_light_palette(self):
        """Force light mode colors."""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F3F4F6"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1F2937"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1F2937"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1F2937"))
        self.setPalette(palette)

    def _setup_ui(self):
        """Build the UI layout."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Server Status Card
        self._setup_server_card(layout)

        # Logs Card
        self._setup_logs_card(layout)

        # Settings Card (thresholds and sounds)
        self._setup_settings_card(layout)

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.setSpacing(6)

        # Logo icon
        icon_label = QLabel()
        if getattr(sys, 'frozen', False):
            # Running as frozen exe - icon bundled in _MEIPASS
            icon_path = Path(sys._MEIPASS) / "whiteboardq_server" / "resources" / "icon.png"
        else:
            # Development mode
            icon_path = Path(__file__).parent.parent.parent.parent / "whiteboardq_client" / "resources" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        icon_label.setStyleSheet("background: transparent;")
        footer_layout.addWidget(icon_label)

        # Text
        footer_text = QLabel(f"WhiteboardQ Server version {get_version()} — Copyright (c) 2026 John Brantly — Licensed under the GNU General Public License v3.0")
        footer_text.setStyleSheet("color: #6B7280; font-size: 11px; background: transparent;")
        footer_layout.addWidget(footer_text)

        layout.addLayout(footer_layout)

    def _setup_settings_card(self, parent_layout):
        """Setup the Settings card (thresholds and sounds)."""
        self._sound_manager = SoundManager()

        card = Card("Threshold and Sound Settings for all Clients")

        # Two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        # === LEFT COLUMN: Thresholds ===
        threshold_group = QGroupBox("Alert Thresholds (minutes)")
        threshold_group.setMinimumWidth(250)
        threshold_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        threshold_layout = QFormLayout(threshold_group)
        threshold_layout.setContentsMargins(10, 12, 10, 8)

        self.yellow_spin = QSpinBox()
        self.yellow_spin.setRange(1, 120)
        self.yellow_spin.setMinimumWidth(80)
        threshold_layout.addRow("Yellow warning:", self.yellow_spin)

        self.red_spin = QSpinBox()
        self.red_spin.setRange(1, 120)
        self.red_spin.setMinimumWidth(80)
        threshold_layout.addRow("Red warning:", self.red_spin)

        self.overdue_spin = QSpinBox()
        self.overdue_spin.setRange(1, 120)
        self.overdue_spin.setMinimumWidth(80)
        threshold_layout.addRow("Overdue alert:", self.overdue_spin)

        columns_layout.addWidget(threshold_group)

        # === RIGHT COLUMN: Sounds ===
        sound_group = QGroupBox("Sounds")
        sound_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        sound_layout = QFormLayout(sound_group)
        sound_layout.setContentsMargins(10, 12, 10, 8)

        available_sounds = self._sound_manager.get_available_sounds()

        # New message sound
        self.sound_new_combo, self.sound_new_play = self._create_sound_row(available_sounds)
        sound_layout.addRow("New message:", self._make_sound_row(self.sound_new_combo, self.sound_new_play))

        # Yellow warning sound
        self.sound_yellow_combo, self.sound_yellow_play = self._create_sound_row(available_sounds)
        sound_layout.addRow("Yellow warning:", self._make_sound_row(self.sound_yellow_combo, self.sound_yellow_play))

        # Red warning sound
        self.sound_red_combo, self.sound_red_play = self._create_sound_row(available_sounds)
        sound_layout.addRow("Red warning:", self._make_sound_row(self.sound_red_combo, self.sound_red_play))

        # Overdue alert sound
        self.sound_overdue_combo, self.sound_overdue_play = self._create_sound_row(available_sounds)
        sound_layout.addRow("Overdue alert:", self._make_sound_row(self.sound_overdue_combo, self.sound_overdue_play))

        columns_layout.addWidget(sound_group)

        card.addLayout(columns_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.settings_reset_btn = QPushButton("Reset to Defaults")
        self.settings_reset_btn.setObjectName("secondary")
        self.settings_reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(self.settings_reset_btn)

        self.settings_apply_btn = QPushButton("Apply")
        self.settings_apply_btn.setObjectName("activate")
        self.settings_apply_btn.setFixedWidth(80)
        self.settings_apply_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.settings_apply_btn)

        card.addLayout(btn_layout)

        parent_layout.addWidget(card)

        # Load current settings from server
        self._load_settings()

    def _create_sound_row(self, available_sounds: list[str]) -> tuple[QComboBox, QPushButton]:
        """Create a combo box and play button for sound selection."""
        combo = QComboBox()
        combo.addItem("(None)", "")
        for sound in available_sounds:
            combo.addItem(sound, sound)

        play_btn = QPushButton("Play")
        play_btn.setObjectName("secondary")
        play_btn.setFixedWidth(60)
        play_btn.clicked.connect(lambda: self._play_selected_sound(combo))

        return combo, play_btn

    def _make_sound_row(self, combo: QComboBox, play_btn: QPushButton) -> QWidget:
        """Create a widget with combo and play button."""
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(combo, 1)
        row.addWidget(play_btn)
        return widget

    def _play_selected_sound(self, combo: QComboBox) -> None:
        """Play the currently selected sound in the combo box."""
        filename = combo.currentData()
        if filename:
            self._sound_manager.play_sound_file(filename)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        """Set combo box to the given value."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_settings(self) -> None:
        """Load settings from server API."""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://localhost:5000/api/config"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req, timeout=2, context=ctx) as response:
                data = json.loads(response.read().decode())

                # Thresholds
                self.yellow_spin.setValue(data.get("yellow_threshold_minutes", 10))
                self.red_spin.setValue(data.get("red_threshold_minutes", 20))
                self.overdue_spin.setValue(data.get("overdue_threshold_minutes", 30))

                # Sounds
                self._set_combo_value(self.sound_new_combo, data.get("sound_new_message", ""))
                self._set_combo_value(self.sound_yellow_combo, data.get("sound_yellow", "soft.wav"))
                self._set_combo_value(self.sound_red_combo, data.get("sound_red", "chimes.wav"))
                self._set_combo_value(self.sound_overdue_combo, data.get("sound_overdue", "littletrumpet.wav"))
        except Exception:
            # Server not running or not accessible - use defaults
            self._reset_settings()

    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        self.yellow_spin.setValue(10)
        self.red_spin.setValue(20)
        self.overdue_spin.setValue(30)
        self._set_combo_value(self.sound_new_combo, "")
        self._set_combo_value(self.sound_yellow_combo, "soft.wav")
        self._set_combo_value(self.sound_red_combo, "chimes.wav")
        self._set_combo_value(self.sound_overdue_combo, "littletrumpet.wav")

    def _apply_settings(self) -> None:
        """Apply settings via server API."""
        config = {
            "yellow_threshold_minutes": self.yellow_spin.value(),
            "red_threshold_minutes": self.red_spin.value(),
            "overdue_threshold_minutes": self.overdue_spin.value(),
            "sound_new_message": self.sound_new_combo.currentData() or "",
            "sound_yellow": self.sound_yellow_combo.currentData() or "soft.wav",
            "sound_red": self.sound_red_combo.currentData() or "chimes.wav",
            "sound_overdue": self.sound_overdue_combo.currentData() or "littletrumpet.wav",
        }

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = "https://localhost:5000/api/config"
            data = json.dumps(config).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="PUT")
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                if response.status == 200:
                    QMessageBox.information(
                        self,
                        "Settings Applied",
                        "Settings have been saved and broadcast to all connected clients.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Server returned status {response.status}",
                    )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to apply settings:\n{e}\n\nMake sure the server is running.",
            )

    def _setup_server_card(self, parent_layout):
        """Setup the Server Status card."""
        card = Card("Server Status")

        # Status grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        # Row 0: Status indicator | Uptime label
        # Status value (dot + text)
        service_row = QHBoxLayout()
        service_row.setSpacing(6)
        self.service_status_dot = StatusDot()
        self.service_status_text = QLabel("Stopped")
        self.service_status_text.setStyleSheet("font-weight: 500;")
        service_row.addWidget(self.service_status_dot)
        service_row.addWidget(self.service_status_text)
        service_row.addStretch()
        service_container = QWidget()
        service_container.setLayout(service_row)
        grid.addWidget(service_container, 0, 0, 1, 2)

        uptime_label = QLabel("Uptime")
        uptime_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        grid.addWidget(uptime_label, 0, 2)

        # Uptime value
        self.uptime_value = QLabel("—")
        self.uptime_value.setStyleSheet("font-weight: 500; color: #1F2937;")
        grid.addWidget(self.uptime_value, 1, 2)

        # Row 2: Connected Clients | Port
        clients_label = QLabel("Connected Clients")
        clients_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        grid.addWidget(clients_label, 2, 0)

        port_label = QLabel("Port")
        port_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        grid.addWidget(port_label, 2, 2)

        self.clients_value = QLabel("—")
        self.clients_value.setStyleSheet("font-weight: 500; color: #1F2937;")
        grid.addWidget(self.clients_value, 3, 0)

        self.port_value = QLabel("5000")
        self.port_value.setStyleSheet("font-weight: 600; color: #1F2937;")
        grid.addWidget(self.port_value, 3, 2)

        card.addLayout(grid)

        # Service control buttons - text varies by mode
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if self._mode == "frontdesk":
            # FrontDesk: subprocess control - shorter labels
            self.start_btn = QPushButton("Start")
            self.start_btn.setObjectName("start")
            self.start_btn.setFixedWidth(80)
            btn_layout.addWidget(self.start_btn)

            self.stop_btn = QPushButton("Stop")
            self.stop_btn.setObjectName("stop")
            self.stop_btn.setFixedWidth(80)
            btn_layout.addWidget(self.stop_btn)
        else:
            # BackOffice: Windows Service control
            self.start_btn = QPushButton("Start Service")
            self.start_btn.setObjectName("start")
            self.start_btn.setFixedWidth(100)
            btn_layout.addWidget(self.start_btn)

            self.stop_btn = QPushButton("Stop Service")
            self.stop_btn.setObjectName("stop")
            self.stop_btn.setFixedWidth(100)
            btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()

        # Connect button signals
        self.start_btn.clicked.connect(self._start_server)
        self.stop_btn.clicked.connect(self._stop_server)

        card.addLayout(btn_layout)

        parent_layout.addWidget(card)

    def _setup_logs_card(self, parent_layout):
        """Setup the Logs card."""
        card = Card("Logs")

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.view_logs_btn = QPushButton("View Logs")
        self.view_logs_btn.setObjectName("secondary")
        self.view_logs_btn.clicked.connect(self._view_logs)
        btn_layout.addWidget(self.view_logs_btn)

        self.open_folder_btn = QPushButton("Open Log Folder")
        self.open_folder_btn.setObjectName("secondary")
        self.open_folder_btn.clicked.connect(self._open_log_folder)
        btn_layout.addWidget(self.open_folder_btn)

        btn_layout.addStretch()

        card.addLayout(btn_layout)

        parent_layout.addWidget(card)

    def _refresh_status(self):
        """Refresh service status."""
        self._start_status_check()

    def _start_status_check(self):
        """Start background status check (non-blocking)."""
        if self._status_check_pending:
            return  # Already checking

        self._status_check_pending = True

        # Create thread and worker
        self._status_thread = QThread()
        self._status_worker = StatusWorker()
        self._status_worker.set_server_process(self._server_process)
        self._status_worker.moveToThread(self._status_thread)

        # Connect signals
        self._status_thread.started.connect(self._status_worker.run)
        self._status_worker.finished.connect(self._on_status_result)
        self._status_worker.finished.connect(self._status_thread.quit)
        self._status_thread.finished.connect(self._cleanup_status_thread)

        self._status_thread.start()

    def _on_status_result(self, service_running: bool, process_running: bool, clients: int, uptime: int):
        """Handle status check result (runs on main thread)."""
        self._status_check_pending = False

        # In frontdesk mode, ServerController handles status updates
        if self._mode == "frontdesk":
            return

        # BackOffice mode: service-based status display
        if service_running:
            self.service_status_dot.set_color("#22C55E")  # Green
            self.service_status_text.setText("Running")
            self.service_status_text.setStyleSheet("font-weight: 500; color: #166534;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.service_status_dot.set_color("#9CA3AF")  # Gray
            self.service_status_text.setText("Stopped")
            self.service_status_text.setStyleSheet("font-weight: 500; color: #6B7280;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

        # Update clients and uptime
        if service_running:
            self.clients_value.setText(str(clients) if clients >= 0 else "—")
            self.uptime_value.setText(self._format_uptime(uptime) if uptime >= 0 else "—")
        else:
            self.uptime_value.setText("—")
            self.clients_value.setText("—")

    def _cleanup_status_thread(self):
        """Clean up thread objects."""
        if self._status_thread:
            self._status_thread.deleteLater()
            self._status_thread = None
        if self._status_worker:
            self._status_worker.deleteLater()
            self._status_worker = None

    def _refresh_service_status(self):
        """Refresh service status (alias for _start_status_check)."""
        self._start_status_check()

    def _is_service_installed(self) -> bool:
        """Check if WhiteboardQ Windows service is installed."""
        if not HAS_PYWIN32:
            return False
        try:
            win32serviceutil.QueryServiceStatus("WhiteboardQServer")
            return True
        except Exception:
            return False

    def _is_service_running(self) -> bool:
        """Check if WhiteboardQ Windows service is running."""
        if HAS_PYWIN32:
            try:
                status = win32serviceutil.QueryServiceStatus("WhiteboardQServer")
                return status[1] == win32service.SERVICE_RUNNING
            except Exception:
                return False
        else:
            # Fallback to sc command
            try:
                result = subprocess.run(
                    ["sc", "query", "WhiteboardQServer"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return "RUNNING" in result.stdout
            except Exception:
                return False

    def _is_process_running(self) -> bool:
        """Check if WhiteboardQ server process is running."""
        # Check our tracked process first
        if self._server_process and self._server_process.poll() is None:
            return True

        # Also check for any WhiteboardQ-Server.exe processes
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq WhiteboardQ-Server.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # tasklist returns header + data rows if process exists
            lines = result.stdout.strip().split("\n")
            return len(lines) > 1 and "WhiteboardQ-Server.exe" in result.stdout
        except Exception:
            return False

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime seconds into human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        elif seconds < 86400:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"

    def _get_server_exe_path(self) -> Path:
        """Get path to WhiteboardQ-Server.exe."""
        if getattr(sys, "frozen", False):
            # Running as compiled exe - server is in same folder
            return Path(sys.executable).parent / "WhiteboardQ-Server.exe"
        else:
            # Development mode
            return Path(__file__).parent.parent.parent / "dist" / "WhiteboardQ-Server.exe"

    def _start_server(self):
        """Start the server (as service in BackOffice mode, subprocess in FrontDesk mode)."""
        # In frontdesk mode, delegate to the ServerController
        if self._mode == "frontdesk" and self._tray_manager is not None:
            self._tray_manager.controller.start()
            return

        # BackOffice mode: control Windows Service
        if not HAS_PYWIN32:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "pywin32 is required for service control.",
            )
            return

        # Check if service is installed
        if not self._is_service_installed():
            QMessageBox.warning(
                self,
                "Service Not Installed",
                "The WhiteboardQ Windows service is not installed.\n\n"
                "Please reinstall WhiteboardQ Server.",
            )
            return

        if self._is_service_running():
            QMessageBox.information(self, "Already Running", "Service is already running.")
            return

        # Show "Starting..." feedback immediately
        self.start_btn.setEnabled(False)
        self.service_status_dot.set_color("#F59E0B")  # Yellow/orange
        self.service_status_text.setText("Starting...")
        self.service_status_text.setStyleSheet("font-weight: 500; color: #92400E;")

        try:
            win32serviceutil.StartService("WhiteboardQServer")
            # Refresh status after a short delay to show "Running"
            QTimer.singleShot(2000, self._refresh_service_status)
        except Exception as e:
            self._refresh_service_status()  # Reset UI
            QMessageBox.critical(
                self,
                "Start Failed",
                f"Failed to start service:\n{e}\n\n"
                "Note: Starting a Windows Service requires administrator privileges.\n"
                "Right-click the application and select 'Run as administrator'.",
            )

    def _stop_server(self):
        """Stop the server (service in BackOffice mode, subprocess in FrontDesk mode)."""
        # In frontdesk mode, delegate to the ServerController
        if self._mode == "frontdesk" and self._tray_manager is not None:
            self._tray_manager.controller.stop()
            return

        # BackOffice mode: control Windows Service
        if not HAS_PYWIN32:
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "pywin32 is required for service control.",
            )
            return

        if not self._is_service_running():
            QMessageBox.information(self, "Already Stopped", "Service is not running.")
            return

        # Show "Stopping..." feedback immediately
        self.stop_btn.setEnabled(False)
        self.service_status_dot.set_color("#F59E0B")  # Yellow/orange
        self.service_status_text.setText("Stopping...")
        self.service_status_text.setStyleSheet("font-weight: 500; color: #92400E;")

        try:
            win32serviceutil.StopService("WhiteboardQServer")
            # Refresh status after a short delay
            QTimer.singleShot(2000, self._refresh_service_status)
        except Exception as e:
            self._refresh_service_status()  # Reset UI
            QMessageBox.critical(
                self,
                "Stop Failed",
                f"Failed to stop service:\n{e}\n\n"
                "Note: Stopping a Windows Service requires administrator privileges.\n"
                "Right-click the application and select 'Run as administrator'.",
            )

    def _view_logs(self):
        """Open log viewer."""
        log_file = self.log_dir / "server.log"
        if log_file.exists():
            os.startfile(str(log_file))
        else:
            QMessageBox.information(
                self,
                "No Logs",
                f"No log file found at:\n{log_file}",
            )

    def _open_log_folder(self):
        """Open log folder in Explorer."""
        if self.log_dir.exists():
            os.startfile(str(self.log_dir))
        else:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.log_dir))
