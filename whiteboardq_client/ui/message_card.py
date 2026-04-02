"""Individual message widget with color-coded aging states."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel

from ..theme import Theme


class MessageState(Enum):
    """Visual state based on message age."""
    NORMAL = "normal"
    YELLOW = "yellow"
    RED = "red"
    OVERDUE = "overdue"


class MessageCard(QFrame):
    """Widget displaying a single message."""

    clicked = Signal(str)  # Emits message_id when clicked
    state_changed = Signal(str, object)  # Emits (message_id, new_state) on state transition

    def __init__(
        self,
        message_id: str,
        content: str,
        station_name: str,
        created_at: datetime,
        position: int,
        theme: Theme,
        yellow_minutes: int = 10,
        red_minutes: int = 20,
        overdue_minutes: int = 30,
        is_important: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.message_id = message_id
        self.content = content
        self.station_name = station_name
        self.created_at = created_at
        self.position = position
        self.theme = theme
        self.yellow_minutes = yellow_minutes
        self.red_minutes = red_minutes
        self.overdue_minutes = overdue_minutes
        self.is_important = is_important

        self._selected = False
        self._state = MessageState.NORMAL
        self._flash_visible = True

        self._setup_ui()
        self._setup_timer()
        self._update_state()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header row: important indicator, station name, time, age badge
        header = QHBoxLayout()
        header.setSpacing(8)

        # Important indicator
        self.important_label = QLabel("!")
        self.important_label.setFixedWidth(20)
        self.important_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.important_label.setStyleSheet(f"""
            color: {self.theme.yellow};
            font-weight: bold;
            font-size: 16px;
        """)
        self.important_label.setVisible(self.is_important)
        header.addWidget(self.important_label)

        self.station_label = QLabel(self.station_name)
        self.station_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {self.theme.accent_blue};")
        header.addWidget(self.station_label)

        self.time_label = QLabel(self._format_time())
        self.time_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 12px;")
        header.addWidget(self.time_label)

        header.addStretch()

        self.age_badge = QLabel()
        self.age_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.age_badge.setMinimumWidth(70)
        header.addWidget(self.age_badge)

        layout.addLayout(header)

        # Content
        self.content_label = QLabel(self.content)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 14px;")
        layout.addWidget(self.content_label)

        self._apply_style()

    def _setup_timer(self) -> None:
        """Setup timer for age updates."""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_state)
        self.update_timer.start(1000)  # Update every second

        # Flash timer for overdue state
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self._toggle_flash)

    def _format_time(self) -> str:
        """Format created_at time."""
        local_time = self.created_at.astimezone()
        return local_time.strftime("%H:%M")

    def _get_age_minutes(self) -> int:
        """Get message age in minutes."""
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        return int(delta.total_seconds() / 60)

    def _get_age_text(self) -> str:
        """Get human-readable age text."""
        minutes = self._get_age_minutes()
        if minutes < 1:
            return "now"
        elif minutes < 60:
            return f"{minutes} min"
        else:
            hours = minutes // 60
            return f"{hours}h {minutes % 60}m"

    def _calculate_state(self) -> MessageState:
        """Determine state based on age."""
        minutes = self._get_age_minutes()
        if minutes >= self.overdue_minutes:
            return MessageState.OVERDUE
        elif minutes >= self.red_minutes:
            return MessageState.RED
        elif minutes >= self.yellow_minutes:
            return MessageState.YELLOW
        return MessageState.NORMAL

    def _update_state(self) -> None:
        """Update visual state based on age."""
        old_state = self._state
        self._state = self._calculate_state()

        # Update age badge
        self._update_age_badge()

        # Handle state transitions
        if old_state != self._state:
            self._apply_style()

            # Start/stop flash timer
            if self._state == MessageState.OVERDUE:
                self.flash_timer.start(750)  # Pulse every 750ms (1.5s cycle)
            else:
                self.flash_timer.stop()
                self._flash_visible = True

            # Emit signal for sound notification (only for escalations, not initial state)
            if old_state != MessageState.NORMAL or self._state != MessageState.NORMAL:
                self.state_changed.emit(self.message_id, self._state)

    def _update_age_badge(self) -> None:
        """Update the age badge display."""
        age_text = self._get_age_text()
        minutes = self._get_age_minutes()

        if self._state == MessageState.OVERDUE:
            self.age_badge.setText("⚠ OVERDUE")
            badge_bg = "rgba(239, 68, 68, 0.3)"
            badge_color = self.theme.badge_text
        elif self._state == MessageState.RED:
            self.age_badge.setText(age_text.upper())
            badge_bg = "rgba(239, 68, 68, 0.2)"
            badge_color = self.theme.badge_text
        elif self._state == MessageState.YELLOW:
            self.age_badge.setText(age_text.upper())
            badge_bg = "rgba(234, 179, 8, 0.2)"
            badge_color = self.theme.badge_text
        elif minutes < 1:
            self.age_badge.setText("NOW")
            badge_bg = "rgba(59, 130, 246, 0.2)"
            badge_color = self.theme.badge_text
        else:
            self.age_badge.setText(age_text.upper())
            badge_bg = "rgba(102, 102, 102, 0.2)"
            badge_color = self.theme.badge_text

        self.age_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        """)

    def _toggle_flash(self) -> None:
        """Toggle flash visibility for overdue state."""
        self._flash_visible = not self._flash_visible
        self._apply_style()

    def _apply_style(self) -> None:
        """Apply styling based on state and selection."""
        # Determine colors based on state
        if self._state == MessageState.OVERDUE:
            if self._flash_visible:
                bg_color = self.theme.overdue_bg
            else:
                bg_color = self.theme.red_bg
            stripe_color = self.theme.red
        elif self._state == MessageState.RED:
            bg_color = self.theme.red_bg
            stripe_color = self.theme.red
        elif self._state == MessageState.YELLOW:
            bg_color = self.theme.yellow_bg
            stripe_color = self.theme.yellow
        else:
            bg_color = self.theme.bg_card
            stripe_color = self.theme.border_card

        # Border color - accent when selected, otherwise subtle
        if self._selected:
            border_color = self.theme.accent
        else:
            border_color = self.theme.border_card

        self.setStyleSheet(f"""
            MessageCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-left: 4px solid {stripe_color};
                border-radius: 12px;
            }}
        """)

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self._selected = selected
        self._apply_style()

    def is_selected(self) -> bool:
        """Check if selected."""
        return self._selected

    def set_theme(self, theme: Theme) -> None:
        """Update theme."""
        self.theme = theme
        self.station_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {theme.accent_blue};")
        self.time_label.setStyleSheet(f"color: {theme.text_muted}; font-size: 12px;")
        self.content_label.setStyleSheet(f"color: {theme.text_primary}; font-size: 14px;")
        self.important_label.setStyleSheet(f"""
            color: {theme.yellow};
            font-weight: bold;
            font-size: 16px;
        """)
        self._update_age_badge()
        self._apply_style()

    def set_important(self, is_important: bool) -> None:
        """Set important flag."""
        self.is_important = is_important
        self.important_label.setVisible(is_important)

    def set_thresholds(self, yellow: int, red: int, overdue: int) -> None:
        """Update threshold values."""
        self.yellow_minutes = yellow
        self.red_minutes = red
        self.overdue_minutes = overdue
        self._update_state()

    def get_state(self) -> MessageState:
        """Get current message state."""
        return self._state

    def mousePressEvent(self, event) -> None:
        """Handle mouse click."""
        self.clicked.emit(self.message_id)
        super().mousePressEvent(event)

    def cleanup(self) -> None:
        """Stop timers before deletion."""
        self.update_timer.stop()
        self.flash_timer.stop()
