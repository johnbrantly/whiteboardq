"""Floating toast notification with undo button after delete."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from ..theme import Theme


class UndoToast(QFrame):
    """Floating toast notification with undo button."""

    undo_clicked = Signal()
    dismissed = Signal()

    DURATION_SECONDS = 10

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._seconds_remaining = self.DURATION_SECONDS
        self._deleted_message_id = None
        self._setup_ui()
        self._setup_timer()
        self.hide()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Message
        self.message_label = QLabel("Message deleted")
        layout.addWidget(self.message_label)

        # Undo button
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setProperty("accent", True)
        self.undo_btn.clicked.connect(self._on_undo)
        layout.addWidget(self.undo_btn)

        layout.addStretch()

        # Countdown
        self.countdown_label = QLabel()
        self.countdown_label.setFixedWidth(30)
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.countdown_label)

        self._apply_style()

    def _setup_timer(self) -> None:
        """Setup countdown timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def _apply_style(self) -> None:
        """Apply styling."""
        self.setStyleSheet(f"""
            UndoToast {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 12px;
            }}
        """)
        self.message_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 14px;")
        self.countdown_label.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 12px;")

        # Undo button styling
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                color: white;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
            }}
        """)

    def set_theme(self, theme: Theme) -> None:
        """Update theme."""
        self.theme = theme
        self._apply_style()

    def show_toast(self, message_id: str) -> None:
        """Show toast with countdown."""
        self._deleted_message_id = message_id
        self._seconds_remaining = self.DURATION_SECONDS
        self._update_countdown()
        self.timer.start(1000)
        self.show()

    def hide_toast(self) -> None:
        """Hide toast and stop timer."""
        self.timer.stop()
        self._deleted_message_id = None
        self.hide()
        self.dismissed.emit()

    def _tick(self) -> None:
        """Handle timer tick."""
        self._seconds_remaining -= 1
        self._update_countdown()

        if self._seconds_remaining <= 0:
            self.hide_toast()

    def _update_countdown(self) -> None:
        """Update countdown display."""
        self.countdown_label.setText(f"{self._seconds_remaining}s")

    def _on_undo(self) -> None:
        """Handle undo click."""
        self.undo_clicked.emit()
        self.hide_toast()

    def get_deleted_message_id(self) -> str:
        """Get the ID of the deleted message."""
        return self._deleted_message_id

    def has_pending_undo(self) -> bool:
        """Check if there's a pending undo."""
        return self._deleted_message_id is not None and self.isVisible()
