"""Message input bar with send button."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFrame

from ..theme import Theme


class ChatBar(QFrame):
    """Input bar for sending messages."""

    message_submitted = Signal(str)  # Emits message content

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Input field
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message and press Enter...")
        self.input.returnPressed.connect(self._submit)
        layout.addWidget(self.input)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setProperty("accent", True)
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._submit)
        layout.addWidget(self.send_btn)

        self._apply_style()

    def _apply_style(self) -> None:
        """Apply styling."""
        self.setStyleSheet(f"""
            ChatBar {{
                background-color: {self.theme.bg_secondary};
                border: none;
                border-top: 1px solid {self.theme.border};
            }}
        """)

        # Input field styling
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.bg_primary};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 12px 16px;
                color: {self.theme.text_primary};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme.accent};
                border-width: 2px;
            }}
        """)

        # Send button styling
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: white;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                color: {self.theme.text_secondary};
            }}
        """)

    def set_theme(self, theme: Theme) -> None:
        """Update theme."""
        self.theme = theme
        self._apply_style()

    def _submit(self) -> None:
        """Submit the current message."""
        text = self.input.text().strip()
        if text:
            self.message_submitted.emit(text)
            self.input.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable input."""
        self.input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.input.setPlaceholderText("Type a message and press Enter...")
        else:
            self.input.setPlaceholderText("Please wait, connecting to server...")

    def focus_input(self) -> None:
        """Focus the input field."""
        self.input.setFocus()
