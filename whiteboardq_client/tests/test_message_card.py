from datetime import datetime, timezone, timedelta

import pytest
from PySide6.QtWidgets import QApplication

from whiteboardq_client.theme import THEMES
from whiteboardq_client.ui.message_card import MessageCard, MessageState


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def theme():
    """Get dark theme."""
    return THEMES["dark"]


@pytest.fixture
def recent_message(app, theme):
    """Create a recently created message card."""
    card = MessageCard(
        message_id="test-1",
        content="Test message content",
        station_name="Front-Desk",
        created_at=datetime.now(timezone.utc),
        position=0,
        theme=theme,
    )
    yield card
    card.cleanup()


class TestMessageCard:
    """Tests for MessageCard widget."""

    def test_initial_state(self, recent_message):
        """Test message card initial state."""
        assert recent_message.message_id == "test-1"
        assert recent_message.content == "Test message content"
        assert recent_message.station_name == "Front-Desk"
        assert recent_message.position == 0
        assert recent_message.is_selected() is False
        assert recent_message.get_state() == MessageState.NORMAL

    def test_selection(self, recent_message):
        """Test selecting and deselecting."""
        recent_message.set_selected(True)
        assert recent_message.is_selected() is True

        recent_message.set_selected(False)
        assert recent_message.is_selected() is False

    def test_state_normal(self, app, theme):
        """Test normal state for recent message."""
        card = MessageCard(
            message_id="test-normal",
            content="Normal message",
            station_name="Station",
            created_at=datetime.now(timezone.utc),
            position=0,
            theme=theme,
            yellow_minutes=10,
            red_minutes=20,
            overdue_minutes=30,
        )
        assert card.get_state() == MessageState.NORMAL
        card.cleanup()

    def test_state_yellow(self, app, theme):
        """Test yellow state for 10+ minute old message."""
        card = MessageCard(
            message_id="test-yellow",
            content="Yellow message",
            station_name="Station",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=12),
            position=0,
            theme=theme,
            yellow_minutes=10,
            red_minutes=20,
            overdue_minutes=30,
        )
        assert card.get_state() == MessageState.YELLOW
        card.cleanup()

    def test_state_red(self, app, theme):
        """Test red state for 20+ minute old message."""
        card = MessageCard(
            message_id="test-red",
            content="Red message",
            station_name="Station",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=22),
            position=0,
            theme=theme,
            yellow_minutes=10,
            red_minutes=20,
            overdue_minutes=30,
        )
        assert card.get_state() == MessageState.RED
        card.cleanup()

    def test_state_overdue(self, app, theme):
        """Test overdue state for 30+ minute old message."""
        card = MessageCard(
            message_id="test-overdue",
            content="Overdue message",
            station_name="Station",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=35),
            position=0,
            theme=theme,
            yellow_minutes=10,
            red_minutes=20,
            overdue_minutes=30,
        )
        assert card.get_state() == MessageState.OVERDUE
        card.cleanup()

    def test_threshold_change(self, app, theme):
        """Test changing thresholds updates state."""
        card = MessageCard(
            message_id="test-threshold",
            content="Threshold test",
            station_name="Station",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=8),
            position=0,
            theme=theme,
            yellow_minutes=10,
            red_minutes=20,
            overdue_minutes=30,
        )
        assert card.get_state() == MessageState.NORMAL

        # Lower yellow threshold
        card.set_thresholds(5, 15, 25)
        assert card.get_state() == MessageState.YELLOW
        card.cleanup()

    def test_important_flag(self, app, theme):
        """Test important flag."""
        card = MessageCard(
            message_id="test-important",
            content="Important test",
            station_name="Station",
            created_at=datetime.now(timezone.utc),
            position=0,
            theme=theme,
            is_important=False,
        )
        assert card.is_important is False

        card.set_important(True)
        assert card.is_important is True

        card.set_important(False)
        assert card.is_important is False
        card.cleanup()

    def test_theme_change(self, app, theme):
        """Test theme change."""
        card = MessageCard(
            message_id="test-theme",
            content="Theme test",
            station_name="Station",
            created_at=datetime.now(timezone.utc),
            position=0,
            theme=theme,
        )
        light_theme = THEMES["light"]
        card.set_theme(light_theme)
        assert card.theme == light_theme
        card.cleanup()

    def test_cleanup(self, app, theme):
        """Test cleanup stops timers."""
        card = MessageCard(
            message_id="test-cleanup",
            content="Cleanup test",
            station_name="Station",
            created_at=datetime.now(timezone.utc),
            position=0,
            theme=theme,
        )
        card.cleanup()
        assert not card.update_timer.isActive()
        assert not card.flash_timer.isActive()
