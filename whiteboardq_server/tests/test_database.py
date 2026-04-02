import pytest
import pytest_asyncio

from whiteboardq_server.database import Database
from whiteboardq_server.models import ServerConfig


@pytest.mark.asyncio
async def test_create_message(test_db: Database):
    """Test creating a message."""
    message = await test_db.create_message("Test content", "Front-Desk")

    assert message.id is not None
    assert message.content == "Test content"
    assert message.station_name == "Front-Desk"
    assert message.position == 1


@pytest.mark.asyncio
async def test_get_messages_ordering(test_db: Database):
    """Test that messages are returned in position order."""
    await test_db.create_message("First", "Station-1")
    await test_db.create_message("Second", "Station-2")
    await test_db.create_message("Third", "Station-3")

    messages = await test_db.get_messages()

    assert len(messages) == 3
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"
    assert messages[0].position < messages[1].position < messages[2].position


@pytest.mark.asyncio
async def test_move_message_up(test_db: Database):
    """Test moving a message up."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    result = await test_db.move_message(msg2.id, "up", "Station-2")
    assert result is not None
    new_position, updates = result

    messages = await test_db.get_messages()
    assert messages[0].id == msg2.id
    assert messages[1].id == msg1.id


@pytest.mark.asyncio
async def test_move_message_down(test_db: Database):
    """Test moving a message down."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    result = await test_db.move_message(msg1.id, "down", "Station-1")
    assert result is not None

    messages = await test_db.get_messages()
    assert messages[0].id == msg2.id
    assert messages[1].id == msg1.id


@pytest.mark.asyncio
async def test_move_message_to_top(test_db: Database):
    """Test moving a message to top."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")
    msg3 = await test_db.create_message("Third", "Station-3")

    result = await test_db.move_message(msg3.id, "top", "Station-3")
    assert result is not None

    messages = await test_db.get_messages()
    assert messages[0].id == msg3.id


@pytest.mark.asyncio
async def test_delete_message(test_db: Database):
    """Test soft deleting a message."""
    msg = await test_db.create_message("To delete", "Station-1")

    deleted = await test_db.delete_message(msg.id, "Station-2")
    assert deleted is not None
    assert deleted.id == msg.id

    messages = await test_db.get_messages()
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_restore_message(test_db: Database):
    """Test restoring a soft-deleted message."""
    msg = await test_db.create_message("To restore", "Station-1")
    await test_db.delete_message(msg.id, "Station-2")

    restored = await test_db.restore_message(msg.id, "Station-3")
    assert restored is not None
    assert restored.id == msg.id

    messages = await test_db.get_messages()
    assert len(messages) == 1
    assert messages[0].id == msg.id


@pytest.mark.asyncio
async def test_get_nonexistent_message(test_db: Database):
    """Test getting a message that doesn't exist."""
    message = await test_db.get_message("nonexistent-id")
    assert message is None


@pytest.mark.asyncio
async def test_delete_nonexistent_message(test_db: Database):
    """Test deleting a message that doesn't exist."""
    result = await test_db.delete_message("nonexistent-id", "Station-1")
    assert result is None


@pytest.mark.asyncio
async def test_config_get_defaults(test_db: Database):
    """Test getting default config."""
    config = await test_db.get_config()

    assert config.yellow_threshold_minutes == 10
    assert config.red_threshold_minutes == 20
    assert config.overdue_threshold_minutes == 30


@pytest.mark.asyncio
async def test_config_set_and_get(test_db: Database):
    """Test setting and getting config."""
    new_config = ServerConfig(
        yellow_threshold_minutes=5,
        red_threshold_minutes=15,
        overdue_threshold_minutes=25,
    )
    await test_db.set_config(new_config)

    config = await test_db.get_config()
    assert config.yellow_threshold_minutes == 5
    assert config.red_threshold_minutes == 15
    assert config.overdue_threshold_minutes == 25


# =============================================================================
# WIPE & RESTORE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_wipe_all_messages(test_db: Database):
    """Test wipe_all deletes all messages and stores IDs for restore."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")
    msg3 = await test_db.create_message("Third", "Station-3")

    deleted_ids = await test_db.wipe_all_messages("Admin")

    assert len(deleted_ids) == 3
    assert msg1.id in deleted_ids
    assert msg2.id in deleted_ids
    assert msg3.id in deleted_ids

    # All messages should be gone
    messages = await test_db.get_messages()
    assert len(messages) == 0

    # Should have wipe to restore
    assert await test_db.has_wipe_to_restore() is True


@pytest.mark.asyncio
async def test_wipe_all_empty_database(test_db: Database):
    """Test wipe_all on empty database returns empty list."""
    deleted_ids = await test_db.wipe_all_messages("Admin")

    assert deleted_ids == []
    assert await test_db.has_wipe_to_restore() is False


@pytest.mark.asyncio
async def test_restore_last_wipe(test_db: Database):
    """Test full wipe and restore cycle."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    # Wipe
    await test_db.wipe_all_messages("Admin")
    assert len(await test_db.get_messages()) == 0

    # Restore
    restored = await test_db.restore_last_wipe("Admin")

    assert len(restored) == 2
    messages = await test_db.get_messages()
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_restore_last_wipe_empty(test_db: Database):
    """Test restore_last_wipe with nothing to restore."""
    # Never wiped anything
    restored = await test_db.restore_last_wipe("Admin")
    assert restored == []


@pytest.mark.asyncio
async def test_restore_clears_wipe_ids(test_db: Database):
    """Test that restore can only be done once."""
    await test_db.create_message("Test", "Station-1")
    await test_db.wipe_all_messages("Admin")

    # First restore works
    restored1 = await test_db.restore_last_wipe("Admin")
    assert len(restored1) == 1

    # Second restore returns nothing (IDs cleared)
    restored2 = await test_db.restore_last_wipe("Admin")
    assert restored2 == []
    assert await test_db.has_wipe_to_restore() is False


@pytest.mark.asyncio
async def test_wipe_then_create_then_restore(test_db: Database):
    """Test that new messages after wipe coexist with restored messages."""
    msg1 = await test_db.create_message("Original", "Station-1")
    await test_db.wipe_all_messages("Admin")

    # Create new message after wipe
    msg2 = await test_db.create_message("New", "Station-2")

    # Restore old messages
    restored = await test_db.restore_last_wipe("Admin")

    messages = await test_db.get_messages()
    assert len(messages) == 2  # Both old and new

    contents = [m.content for m in messages]
    assert "Original" in contents
    assert "New" in contents


@pytest.mark.asyncio
async def test_wipe_restore_survives_restart(tmp_path):
    """Test that wipe restore works after server restart (database reconnect)."""
    db_path = tmp_path / "restart_test.db"

    # First "server session" - create messages and wipe
    db1 = Database(db_path)
    await db1.connect()
    await db1.init_db()

    await db1.create_message("Message 1", "Station-A")
    await db1.create_message("Message 2", "Station-B")
    deleted_ids = await db1.wipe_all_messages("Admin")
    assert len(deleted_ids) == 2
    assert await db1.has_wipe_to_restore() is True

    # Close database (simulating server shutdown)
    await db1.close()

    # Second "server session" - reconnect and restore
    db2 = Database(db_path)
    await db2.connect()
    await db2.init_db()

    # Verify restore is still available after "restart"
    assert await db2.has_wipe_to_restore() is True

    # Restore should work
    restored = await db2.restore_last_wipe("Admin")
    assert len(restored) == 2

    # Messages should be back
    messages = await db2.get_messages()
    assert len(messages) == 2

    await db2.close()


# =============================================================================
# POSITION EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_move_up_at_top(test_db: Database):
    """Test moving up when already at top returns no updates."""
    msg1 = await test_db.create_message("First", "Station-1")
    await test_db.create_message("Second", "Station-2")

    result = await test_db.move_message(msg1.id, "up", "Station-1")

    assert result is not None
    new_pos, updates = result
    assert updates == []  # No movement occurred


@pytest.mark.asyncio
async def test_move_down_at_bottom(test_db: Database):
    """Test moving down when already at bottom returns no updates."""
    await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    result = await test_db.move_message(msg2.id, "down", "Station-2")

    assert result is not None
    new_pos, updates = result
    assert updates == []  # No movement occurred


@pytest.mark.asyncio
async def test_move_top_already_at_top(test_db: Database):
    """Test move-to-top when already at top returns no updates."""
    msg1 = await test_db.create_message("First", "Station-1")
    await test_db.create_message("Second", "Station-2")

    result = await test_db.move_message(msg1.id, "top", "Station-1")

    assert result is not None
    new_pos, updates = result
    assert updates == []  # No movement occurred (already at top)


@pytest.mark.asyncio
async def test_move_single_message(test_db: Database):
    """Test moving when only one message exists."""
    msg = await test_db.create_message("Only", "Station-1")

    # Try all directions
    result_up = await test_db.move_message(msg.id, "up", "Station-1")
    result_down = await test_db.move_message(msg.id, "down", "Station-1")
    result_top = await test_db.move_message(msg.id, "top", "Station-1")

    # All should return no updates (can't move single item)
    assert result_up[1] == []
    assert result_down[1] == []
    assert result_top[1] == []


@pytest.mark.asyncio
async def test_move_nonexistent_message(test_db: Database):
    """Test moving a message that doesn't exist returns None."""
    result = await test_db.move_message("nonexistent-id", "up", "Station-1")
    assert result is None


@pytest.mark.asyncio
async def test_position_goes_negative(test_db: Database):
    """Test that move-to-top can result in negative positions."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")
    msg3 = await test_db.create_message("Third", "Station-3")

    # Move msg3 to top repeatedly
    await test_db.move_message(msg3.id, "top", "Station-3")
    await test_db.move_message(msg2.id, "top", "Station-2")

    messages = await test_db.get_messages()

    # Position should be negative after multiple move-to-top operations
    min_position = min(m.position for m in messages)
    assert min_position < 1  # Position went below 1

    # But ordering should still work
    assert messages[0].id == msg2.id
    assert messages[1].id == msg3.id
    assert messages[2].id == msg1.id


@pytest.mark.asyncio
async def test_positions_after_delete(test_db: Database):
    """Test that positions remain correct after deleting middle message."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")
    msg3 = await test_db.create_message("Third", "Station-3")

    # Delete middle message
    await test_db.delete_message(msg2.id, "Admin")

    messages = await test_db.get_messages()
    assert len(messages) == 2
    assert messages[0].id == msg1.id
    assert messages[1].id == msg3.id

    # Positions may be sparse but ordering is preserved
    assert messages[0].position < messages[1].position


# =============================================================================
# RESTORE EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_restore_already_active(test_db: Database):
    """Test that restoring an active (non-deleted) message returns None."""
    msg = await test_db.create_message("Active", "Station-1")

    result = await test_db.restore_message(msg.id, "Admin")
    assert result is None


@pytest.mark.asyncio
async def test_restore_nonexistent(test_db: Database):
    """Test that restoring a nonexistent message returns None."""
    result = await test_db.restore_message("nonexistent-id", "Admin")
    assert result is None


@pytest.mark.asyncio
async def test_restore_position_assignment(test_db: Database):
    """Test that restored message gets position at end of list."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    # Delete and restore first message
    await test_db.delete_message(msg1.id, "Admin")
    restored = await test_db.restore_message(msg1.id, "Admin")

    # Restored message should be at the bottom
    messages = await test_db.get_messages()
    assert messages[-1].id == restored.id
    assert restored.position > msg2.position


@pytest.mark.asyncio
async def test_restore_after_all_deleted(test_db: Database):
    """Test restoring when all other messages are deleted."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    # Delete both
    await test_db.delete_message(msg1.id, "Admin")
    await test_db.delete_message(msg2.id, "Admin")

    # Restore one
    restored = await test_db.restore_message(msg1.id, "Admin")

    # Should get position 1
    assert restored.position == 1
    messages = await test_db.get_messages()
    assert len(messages) == 1


# =============================================================================
# EMPTY/BOUNDARY TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_messages_empty(test_db: Database):
    """Test get_messages on empty database returns empty list."""
    messages = await test_db.get_messages()
    assert messages == []


@pytest.mark.asyncio
async def test_get_message_empty_db(test_db: Database):
    """Test get_message on empty database returns None."""
    message = await test_db.get_message("any-id")
    assert message is None


@pytest.mark.asyncio
async def test_create_first_message(test_db: Database):
    """Test that first message gets position 1."""
    msg = await test_db.create_message("First", "Station-1")
    assert msg.position == 1


@pytest.mark.asyncio
async def test_create_message_empty_content(test_db: Database):
    """Test creating a message with empty content."""
    # Database allows it - validation should be at API layer
    msg = await test_db.create_message("", "Station-1")
    assert msg.content == ""
    assert msg.id is not None


# =============================================================================
# HISTORY LOGGING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_create_logs_history(test_db: Database):
    """Test that creating a message logs to history."""
    msg = await test_db.create_message("Test", "Station-1")

    cursor = await test_db.conn.execute(
        "SELECT action, actor_station FROM message_history WHERE message_id = ?",
        (msg.id,),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["action"] == "created"
    assert row["actor_station"] == "Station-1"


@pytest.mark.asyncio
async def test_delete_logs_history(test_db: Database):
    """Test that deleting a message logs to history."""
    msg = await test_db.create_message("Test", "Station-1")
    await test_db.delete_message(msg.id, "Station-2")

    cursor = await test_db.conn.execute(
        "SELECT action, actor_station FROM message_history WHERE message_id = ? AND action = 'deleted'",
        (msg.id,),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["action"] == "deleted"
    assert row["actor_station"] == "Station-2"


@pytest.mark.asyncio
async def test_restore_logs_history(test_db: Database):
    """Test that restoring a message logs to history."""
    msg = await test_db.create_message("Test", "Station-1")
    await test_db.delete_message(msg.id, "Station-1")
    await test_db.restore_message(msg.id, "Station-3")

    cursor = await test_db.conn.execute(
        "SELECT action, actor_station FROM message_history WHERE message_id = ? AND action = 'restored'",
        (msg.id,),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["action"] == "restored"
    assert row["actor_station"] == "Station-3"


@pytest.mark.asyncio
async def test_move_logs_history(test_db: Database):
    """Test that moving a message logs to history with details."""
    import json

    msg1 = await test_db.create_message("First", "Station-1")
    await test_db.create_message("Second", "Station-2")

    await test_db.move_message(msg1.id, "down", "Station-1")

    cursor = await test_db.conn.execute(
        "SELECT action, actor_station, details FROM message_history WHERE message_id = ? AND action = 'moved'",
        (msg1.id,),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["action"] == "moved"
    assert row["actor_station"] == "Station-1"

    details = json.loads(row["details"])
    assert details["direction"] == "down"
    assert "new_position" in details


@pytest.mark.asyncio
async def test_wipe_logs_history(test_db: Database):
    """Test that wipe_all logs history for each message."""
    msg1 = await test_db.create_message("First", "Station-1")
    msg2 = await test_db.create_message("Second", "Station-2")

    await test_db.wipe_all_messages("Admin")

    # Check history for both messages
    cursor = await test_db.conn.execute(
        "SELECT message_id FROM message_history WHERE action = 'deleted' AND actor_station = 'Admin'"
    )
    rows = await cursor.fetchall()

    deleted_ids = [row["message_id"] for row in rows]
    assert msg1.id in deleted_ids
    assert msg2.id in deleted_ids
