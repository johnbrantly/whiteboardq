"""Top status bar — connection state, station name, PHI notice."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame

from ..theme import Theme


class StatusBar(QFrame):
    """Status bar showing connection status and PHI notice."""

    # Connection states
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._connection_state = self.CONNECTING
        self._station_name = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)

        # === LEFT SECTION ===
        left_section = QWidget()
        left_layout = QHBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Connection indicator (dot)
        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(16)
        left_layout.addWidget(self.status_dot)

        # Connection text
        self.status_text = QLabel("Connecting...")
        left_layout.addWidget(self.status_text)

        # Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.Shape.VLine)
        self.divider.setFixedWidth(1)
        self.divider.setFixedHeight(20)
        left_layout.addSpacing(12)
        left_layout.addWidget(self.divider)
        left_layout.addSpacing(12)

        # Station name
        self.station_label = QLabel("")
        left_layout.addWidget(self.station_label)

        layout.addWidget(left_section)
        layout.addStretch()

        # === RIGHT-JUSTIFIED with message area (not sidebar) ===
        self.phi_notice = QFrame()
        phi_layout = QHBoxLayout(self.phi_notice)
        phi_layout.setContentsMargins(16, 8, 16, 8)

        self.phi_label = QLabel("NO PHI")
        phi_layout.addWidget(self.phi_label)

        layout.addWidget(self.phi_notice)

        # Spacer matching sidebar width so pill aligns with message area edge
        sidebar_spacer = QWidget()
        sidebar_spacer.setFixedWidth(100)
        layout.addWidget(sidebar_spacer)

        self._apply_style()

    def _apply_style(self) -> None:
        """Apply styling based on theme."""
        # Status bar background
        self.setStyleSheet(f"""
            StatusBar {{
                background-color: {self.theme.bg_secondary};
                border: none;
                border-bottom: 1px solid {self.theme.border};
            }}
        """)

        # Connection indicator color
        if self._connection_state == self.CONNECTED:
            dot_color = self.theme.success
        elif self._connection_state == self.CONNECTING:
            dot_color = self.theme.yellow
        else:
            dot_color = self.theme.red

        self.status_dot.setStyleSheet(f"""
            color: {dot_color};
            font-size: 14px;
        """)

        # Connection text
        self.status_text.setStyleSheet(f"""
            color: {self.theme.text_primary};
            font-size: 13px;
            font-weight: 500;
        """)

        # Divider
        self.divider.setStyleSheet(f"""
            background-color: {self.theme.border};
        """)

        # Station name
        self.station_label.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-size: 13px;
        """)

        # PHI notice box - amber/yellow theme
        if self.theme.name == "dark":
            phi_bg = "#2a2617"
            phi_border = "#eab308"
            phi_label_color = "#eab308"
        else:
            phi_bg = "#fffbeb"
            phi_border = "#f59e0b"
            phi_label_color = "#b45309"

        self.phi_notice.setStyleSheet(f"""
            QFrame {{
                background-color: {phi_bg};
                border: 1px solid {phi_border};
                border-radius: 8px;
            }}
        """)

        self.phi_label.setStyleSheet(f"""
            color: {phi_label_color};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)

    def set_theme(self, theme: Theme) -> None:
        """Update theme."""
        self.theme = theme
        self._apply_style()

    def set_connected(self, connected: bool) -> None:
        """Update connection status."""
        self._connection_state = self.CONNECTED if connected else self.DISCONNECTED
        self.status_text.setText("Connected" if connected else "Disconnected")
        self._apply_style()

    def set_connecting(self) -> None:
        """Set status to connecting."""
        self._connection_state = self.CONNECTING
        self.status_text.setText("Connecting...")
        self.status_text.setToolTip("")
        self._apply_style()

    def set_error(self, error: str) -> None:
        """Set status to error with message."""
        self._connection_state = self.DISCONNECTED
        short_error = error[:50] + "..." if len(error) > 50 else error
        self.status_text.setText(f"Error: {short_error}")
        self.status_text.setToolTip(error)
        self._apply_style()

    def set_station_name(self, name: str) -> None:
        """Update station name display."""
        self._station_name = name
        self.station_label.setText(f"Station: {name}" if name else "")

    def set_thresholds(self, yellow: int, red: int, overdue: int) -> None:
        """Update threshold values (no longer displayed in status bar)."""
        # Thresholds are now only used internally by message cards
        pass

