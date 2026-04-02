"""Sidebar with move, delete, and restore action buttons."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame

from ..theme import Theme


class ControlSidebar(QFrame):
    """Vertical sidebar with action buttons."""

    move_top_clicked = Signal()
    move_up_clicked = Signal()
    move_down_clicked = Signal()
    delete_clicked = Signal()
    restore_clicked = Signal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Action button group (priority, up, down)
        self.action_group = QWidget()
        action_layout = QVBoxLayout(self.action_group)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Priority button (!)
        self.btn_top = QPushButton("!")
        self.btn_top.setToolTip("Mark Priority")
        self.btn_top.setFixedSize(56, 56)
        self.btn_top.clicked.connect(self.move_top_clicked.emit)
        action_layout.addWidget(self.btn_top)

        # Move up button
        self.btn_up = QPushButton("↑")
        self.btn_up.setToolTip("Move Up")
        self.btn_up.setFixedSize(56, 56)
        self.btn_up.clicked.connect(self.move_up_clicked.emit)
        action_layout.addWidget(self.btn_up)

        # Move down button
        self.btn_down = QPushButton("↓")
        self.btn_down.setToolTip("Move Down")
        self.btn_down.setFixedSize(56, 56)
        self.btn_down.clicked.connect(self.move_down_clicked.emit)
        action_layout.addWidget(self.btn_down)

        layout.addWidget(self.action_group)

        # Divider line
        self.divider = QFrame()
        self.divider.setFixedSize(36, 1)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        layout.addSpacing(12)
        layout.addWidget(self.divider, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(12)

        # Delete button
        self.btn_delete = QPushButton("×")
        self.btn_delete.setToolTip("Delete")
        self.btn_delete.setFixedSize(56, 56)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)
        layout.addWidget(self.btn_delete, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Spacer (half flexible)
        layout.addStretch(1)

        # Restore button (text button)
        self.btn_restore = QPushButton("Restore\nlast\ndeleted\nmessage")
        self.btn_restore.setToolTip("Restore last deleted message")
        self.btn_restore.setFixedWidth(70)
        self.btn_restore.clicked.connect(self.restore_clicked.emit)
        layout.addWidget(self.btn_restore, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Bottom spacer (keeps restore button centered in lower half)
        layout.addStretch(1)

        # Initial state: all disabled
        self._selected_id = None
        self.set_selection(None, False, False, False)

        self._apply_style()

    def _apply_style(self) -> None:
        """Apply styling."""
        # Sidebar container
        self.setStyleSheet(f"""
            ControlSidebar {{
                background-color: {self.theme.bg_secondary};
                border: none;
                border-left: 1px solid {self.theme.border};
            }}
        """)

        # Divider styling
        self.divider.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.border};
                border: none;
            }}
        """)

        # Priority button (!) - Yellow
        self.btn_top.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 12px;
                color: {self.theme.yellow};
                font-size: 28px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.yellow_bg};
                border-color: {self.theme.yellow};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                border-color: {self.theme.bg_tertiary};
                color: {self.theme.yellow};
            }}
        """)

        # Move Up button - Blue (accent)
        self.btn_up.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 12px;
                color: {self.theme.accent};
                font-size: 28px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_bg};
                border-color: {self.theme.accent};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                border-color: {self.theme.bg_tertiary};
                color: {self.theme.accent};
            }}
        """)

        # Move Down button - Blue (accent)
        self.btn_down.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 12px;
                color: {self.theme.accent};
                font-size: 28px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_bg};
                border-color: {self.theme.accent};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                border-color: {self.theme.bg_tertiary};
                color: {self.theme.accent};
            }}
        """)

        # Delete button - Red
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 12px;
                color: {self.theme.red};
                font-size: 28px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.red_bg};
                border-color: {self.theme.red};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                border-color: {self.theme.bg_tertiary};
                color: {self.theme.red};
            }}
        """)

        # Restore button - Green text button
        self.btn_restore.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border_card};
                border-radius: 8px;
                color: {self.theme.success};
                font-size: 10px;
                font-weight: 600;
                padding: 8px 10px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {self.theme.success_bg};
                border-color: {self.theme.success};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_tertiary};
                border-color: {self.theme.bg_tertiary};
                color: {self.theme.success};
            }}
        """)

    def set_theme(self, theme: Theme) -> None:
        """Update theme."""
        self.theme = theme
        self._apply_style()

    def set_selection(
        self,
        message_id: str | None,
        is_first: bool,
        is_last: bool,
        is_important: bool = False
    ) -> None:
        """Update button states based on selection."""
        self._selected_id = message_id
        has_selection = message_id is not None

        self.btn_top.setEnabled(has_selection and not is_first)
        self.btn_up.setEnabled(has_selection and not is_first)
        self.btn_down.setEnabled(has_selection and not is_last)
        self.btn_delete.setEnabled(has_selection)

    def set_restore_enabled(self, enabled: bool) -> None:
        """Enable/disable restore button."""
        self.btn_restore.setEnabled(enabled)
