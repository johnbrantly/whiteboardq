"""Confirmation dialog for message deletion."""

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QFrame
)

from ..theme import Theme


class DeleteDialog(QDialog):
    """Confirmation dialog for deleting a message."""

    def __init__(
        self,
        content: str,
        station_name: str,
        created_at: datetime,
        theme: Theme,
        parent=None
    ):
        super().__init__(parent)
        self.content = content
        self.station_name = station_name
        self.created_at = created_at
        self.theme = theme
        self._dont_ask_again = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle("Delete Message?")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Message preview
        preview = QFrame()
        preview.setFrameStyle(QFrame.Shape.StyledPanel)
        preview.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

        preview_layout = QVBoxLayout(preview)
        preview_layout.setSpacing(4)

        # Header
        age = self._get_age_text()
        header = QLabel(f"{self.station_name} at {self._format_time()} ({age})")
        header.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 12px;")
        preview_layout.addWidget(header)

        # Content
        content_label = QLabel(self.content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 14px;")
        preview_layout.addWidget(content_label)

        layout.addWidget(preview)

        # Don't ask again checkbox
        self.dont_ask_cb = QCheckBox("Don't ask again")
        layout.addWidget(self.dont_ask_cb)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.clicked.connect(self._confirm)
        self.delete_btn.setDefault(True)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)

    def _format_time(self) -> str:
        """Format created_at time."""
        local_time = self.created_at.astimezone()
        return local_time.strftime("%H:%M")

    def _get_age_text(self) -> str:
        """Get human-readable age."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "just now"
        elif minutes < 60:
            return f"{minutes} min ago"
        else:
            hours = minutes // 60
            return f"{hours}h ago"

    def _confirm(self) -> None:
        """Confirm deletion."""
        self._dont_ask_again = self.dont_ask_cb.isChecked()
        self.accept()

    def dont_ask_again(self) -> bool:
        """Check if user wants to skip confirmation in future."""
        return self._dont_ask_again

    def keyPressEvent(self, event) -> None:
        """Handle key presses."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._confirm()
        else:
            super().keyPressEvent(event)
