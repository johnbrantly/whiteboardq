"""First-run welcome dialog with PHI disclaimer."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
)

from ..theme import Theme


class WelcomeDialog(QDialog):
    """First-run dialog explaining PHI prohibition."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._dont_show_again = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the dialog UI."""
        self.setWindowTitle("WhiteboardQ")
        self.setFixedWidth(450)
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

        # PHI warning
        warning = QLabel(
            "This application is for <b>operational messages only</b>.<br><br>"
            "Do <b>NOT</b> include Protected Health Information (PHI) such as:<br>"
            "• Patient full names<br>"
            "• Medical conditions or diagnoses<br>"
            "• Treatment details<br>"
            "• Insurance or billing information<br><br>"
            "<b>Good examples:</b> \"Mrs. J ready in Op 2\", \"Room 3 cleaned\"<br>"
            "<b>Bad examples:</b> \"John Smith cavity filling\", \"Jane Doe insurance\""
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(f"""
            color: {self.theme.text_primary};
            background-color: {self.theme.bg_secondary};
            padding: 16px;
            border-radius: 8px;
        """)
        layout.addWidget(warning)

        # Checkbox
        self.checkbox = QCheckBox("Don't show this again")
        self.checkbox.setStyleSheet(f"color: {self.theme.text_secondary};")
        self.checkbox.toggled.connect(self._on_checkbox_toggled)
        layout.addWidget(self.checkbox)

        # Button
        btn = QPushButton("I Understand")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
                opacity: 0.9;
            }}
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        # Dialog style
        self.setStyleSheet(f"""
            WelcomeDialog {{
                background-color: {self.theme.bg_primary};
            }}
        """)

    def _on_checkbox_toggled(self, checked: bool) -> None:
        """Handle checkbox toggle."""
        self._dont_show_again = checked

    @property
    def dont_show_again(self) -> bool:
        """Return whether user wants to skip this dialog in future."""
        return self._dont_show_again
