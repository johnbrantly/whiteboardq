"""Scrollable container managing MessageCard widgets."""

from datetime import datetime
from typing import Optional, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame
)

from ..theme import Theme
from .message_card import MessageCard, MessageState


class MessageList(QScrollArea):
    """Scrollable list of message cards."""

    selection_changed = Signal(object)  # Emits message_id or None if none
    state_changed = Signal(str, object)  # message_id, new_state (for sounds)
    delete_requested = Signal(str)  # message_id for deletion request

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.cards: Dict[str, MessageCard] = {}
        self.selected_id: Optional[str] = None

        # Thresholds (updated from server config)
        self.yellow_minutes = 10
        self.red_minutes = 20
        self.overdue_minutes = 30

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget UI."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Container widget
        self.container = QWidget()
        self.container.setMouseTracking(True)
        self.container.mousePressEvent = self._container_clicked
        self.setWidget(self.container)

        # Layout for cards
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state label
        self.empty_label = QLabel("No messages yet")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 16px; padding: 40px;")
        self.layout.addWidget(self.empty_label)

        self._update_empty_state()

    def _update_empty_state(self) -> None:
        """Show/hide empty state."""
        self.empty_label.setVisible(len(self.cards) == 0)

    def set_theme(self, theme: Theme) -> None:
        """Update theme for all cards."""
        self.theme = theme
        self.empty_label.setStyleSheet(f"color: {theme.text_secondary}; font-size: 16px; padding: 40px;")
        for card in self.cards.values():
            card.set_theme(theme)

    def set_thresholds(self, yellow: int, red: int, overdue: int) -> None:
        """Update threshold values for all cards."""
        self.yellow_minutes = yellow
        self.red_minutes = red
        self.overdue_minutes = overdue
        for card in self.cards.values():
            card.set_thresholds(yellow, red, overdue)

    def add_message(
        self,
        message_id: str,
        content: str,
        station_name: str,
        created_at: datetime,
        position: int,
        is_important: bool = False
    ) -> MessageCard:
        """Add a new message card."""
        if message_id in self.cards:
            return self.cards[message_id]

        card = MessageCard(
            message_id=message_id,
            content=content,
            station_name=station_name,
            created_at=created_at,
            position=position,
            theme=self.theme,
            yellow_minutes=self.yellow_minutes,
            red_minutes=self.red_minutes,
            overdue_minutes=self.overdue_minutes,
            is_important=is_important,
        )
        card.clicked.connect(self._on_card_clicked)
        card.state_changed.connect(self._on_card_state_changed)

        self.cards[message_id] = card
        self._insert_card_at_position(card, position)
        self._update_empty_state()

        return card

    def _insert_card_at_position(self, card: MessageCard, position: int) -> None:
        """Insert card at correct position in layout."""
        # Find insertion index based on position
        insert_index = 0
        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, MessageCard):
                    if widget.position > position:
                        break
                    insert_index = i + 1
                elif widget == self.empty_label:
                    insert_index = i + 1

        self.layout.insertWidget(insert_index, card)

    def remove_message(self, message_id: str) -> None:
        """Remove a message card."""
        if message_id in self.cards:
            card = self.cards.pop(message_id)
            card.cleanup()
            self.layout.removeWidget(card)
            card.deleteLater()

            if self.selected_id == message_id:
                self.selected_id = None
                self.selection_changed.emit(None)

            self._update_empty_state()

    def update_positions(self, positions: List[Dict[str, any]]) -> None:
        """Update positions of messages and reorder layout."""
        # Update position values
        for pos_data in positions:
            msg_id = pos_data.get("id")
            position = pos_data.get("position")
            if msg_id in self.cards:
                self.cards[msg_id].position = position

        # Reorder layout
        self._reorder_layout()

    def _reorder_layout(self) -> None:
        """Reorder cards in layout based on position."""
        # Get sorted cards
        sorted_cards = sorted(self.cards.values(), key=lambda c: c.position)

        # Remove all cards from layout (keep empty label)
        for card in self.cards.values():
            self.layout.removeWidget(card)

        # Re-add in order
        insert_index = 1 if self.empty_label.isVisible() else 0
        for card in sorted_cards:
            self.layout.insertWidget(insert_index, card)
            insert_index += 1

    def clear(self) -> None:
        """Remove all messages."""
        for message_id in list(self.cards.keys()):
            self.remove_message(message_id)
        self.selected_id = None

    def select_message(self, message_id: Optional[str]) -> None:
        """Select a message by ID."""
        # Deselect current
        if self.selected_id and self.selected_id in self.cards:
            self.cards[self.selected_id].set_selected(False)

        # Select new
        self.selected_id = message_id
        if message_id and message_id in self.cards:
            self.cards[message_id].set_selected(True)

        self.selection_changed.emit(message_id)

    def get_selected_id(self) -> Optional[str]:
        """Get currently selected message ID."""
        return self.selected_id

    def get_selected_card(self) -> Optional[MessageCard]:
        """Get currently selected card."""
        if self.selected_id:
            return self.cards.get(self.selected_id)
        return None

    def get_message_ids_sorted(self) -> List[str]:
        """Get message IDs sorted by position."""
        sorted_cards = sorted(self.cards.values(), key=lambda c: c.position)
        return [c.message_id for c in sorted_cards]

    def is_at_top(self, message_id: str) -> bool:
        """Check if message is at top position."""
        sorted_ids = self.get_message_ids_sorted()
        return sorted_ids and sorted_ids[0] == message_id

    def is_at_bottom(self, message_id: str) -> bool:
        """Check if message is at bottom position."""
        sorted_ids = self.get_message_ids_sorted()
        return sorted_ids and sorted_ids[-1] == message_id

    def scroll_to_bottom(self) -> None:
        """Scroll to bottom of list."""
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        )

    def _on_card_clicked(self, message_id: str) -> None:
        """Handle card click."""
        if self.selected_id == message_id:
            # Clicking selected card deselects it
            self.select_message(None)
        else:
            self.select_message(message_id)

    def _on_card_state_changed(self, message_id: str, new_state) -> None:
        """Handle card state change - forward to parent for sound."""
        self.state_changed.emit(message_id, new_state)

    def get_card(self, message_id: str) -> Optional[MessageCard]:
        """Get card by message ID."""
        return self.cards.get(message_id)

    def is_first(self, message_id: str) -> bool:
        """Check if message is first (top) in list."""
        return self.is_at_top(message_id)

    def is_last(self, message_id: str) -> bool:
        """Check if message is last (bottom) in list."""
        return self.is_at_bottom(message_id)

    def update_message(self, message: dict) -> None:
        """Update a message with new data."""
        message_id = message.get("id")
        if message_id not in self.cards:
            return

        card = self.cards[message_id]

        # Update position if changed
        if "position" in message:
            old_position = card.position
            new_position = message["position"]
            if old_position != new_position:
                card.position = new_position
                self._reorder_layout()

        # Update important flag if changed
        if "is_important" in message:
            card.set_important(message["is_important"])

    def keyPressEvent(self, event) -> None:
        """Handle key presses for deletion."""
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            if self.selected_id:
                self.delete_requested.emit(self.selected_id)
        elif event.key() == Qt.Key.Key_Escape:
            self.select_message(None)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        """Handle clicks on empty space to deselect."""
        # Check if click is on a card
        child = self.childAt(event.pos())
        if child is None or child == self.container or child == self.empty_label:
            # Clicked on empty space - deselect
            self.select_message(None)
        super().mousePressEvent(event)

    def _container_clicked(self, event) -> None:
        """Handle clicks on container background to deselect."""
        # Get the widget at click position within container
        child = self.container.childAt(event.pos())
        if child is None or child == self.empty_label:
            # Clicked on empty space - deselect
            self.select_message(None)
