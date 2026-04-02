import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from whiteboardq_server.database import Database
from whiteboardq_server import database


@pytest.fixture
def sync_client(tmp_path):
    """Create synchronous test client for WebSocket tests."""
    import asyncio

    # Setup database
    db_path = tmp_path / "test_ws.db"
    db = Database(db_path)

    async def setup_db():
        await db.connect()
        await db.init_db()

    asyncio.get_event_loop().run_until_complete(setup_db())
    database.db = db

    # Import create_app after setting up env
    from whiteboardq_server.main import create_app
    app = create_app()

    with TestClient(app) as client:
        yield client

    async def cleanup_db():
        await db.close()

    asyncio.get_event_loop().run_until_complete(cleanup_db())


def test_websocket_connect_and_initial_state(sync_client: TestClient):
    """Test WebSocket connection and initial state."""
    with sync_client.websocket_connect("/ws?station=Test-Station") as ws:
        data = ws.receive_json()
        assert data["type"] == "initial_state"
        assert "messages" in data
        assert "config" in data
        assert isinstance(data["messages"], list)


def test_websocket_missing_station(sync_client: TestClient):
    """Test WebSocket connection without station name."""
    with pytest.raises(Exception):
        with sync_client.websocket_connect("/ws") as ws:
            pass


def test_websocket_create_message(sync_client: TestClient):
    """Test creating a message via WebSocket."""
    with sync_client.websocket_connect("/ws?station=Front-Desk") as ws:
        # Get initial state
        initial = ws.receive_json()
        assert initial["type"] == "initial_state"

        # Create message
        ws.send_json({
            "type": "create_message",
            "content": "Hello from WebSocket"
        })

        # Should receive broadcast
        event = ws.receive_json()
        assert event["type"] == "message_created"
        assert event["message"]["content"] == "Hello from WebSocket"
        assert event["message"]["station_name"] == "Front-Desk"


def test_websocket_move_message(sync_client: TestClient):
    """Test moving a message via WebSocket."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        # Initial state
        ws.receive_json()

        # Create two messages
        ws.send_json({"type": "create_message", "content": "First"})
        event1 = ws.receive_json()
        msg1_id = event1["message"]["id"]

        ws.send_json({"type": "create_message", "content": "Second"})
        event2 = ws.receive_json()
        msg2_id = event2["message"]["id"]

        # Move first down
        ws.send_json({
            "type": "move_message",
            "message_id": msg1_id,
            "direction": "down"
        })

        move_event = ws.receive_json()
        assert move_event["type"] == "message_moved"
        assert move_event["message_id"] == msg1_id
        assert move_event["moved_by"] == "Station-1"


def test_websocket_delete_message(sync_client: TestClient):
    """Test deleting a message via WebSocket."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        # Initial state
        ws.receive_json()

        # Create message
        ws.send_json({"type": "create_message", "content": "To delete"})
        event = ws.receive_json()
        msg_id = event["message"]["id"]

        # Delete it
        ws.send_json({
            "type": "delete_message",
            "message_id": msg_id
        })

        delete_event = ws.receive_json()
        assert delete_event["type"] == "message_deleted"
        assert delete_event["message_id"] == msg_id
        assert delete_event["deleted_by"] == "Station-1"


def test_websocket_restore_message(sync_client: TestClient):
    """Test restoring a message via WebSocket."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        # Initial state
        ws.receive_json()

        # Create and delete
        ws.send_json({"type": "create_message", "content": "To restore"})
        event = ws.receive_json()
        msg_id = event["message"]["id"]

        ws.send_json({"type": "delete_message", "message_id": msg_id})
        ws.receive_json()  # delete event

        # Restore
        ws.send_json({
            "type": "restore_message",
            "message_id": msg_id
        })

        restore_event = ws.receive_json()
        assert restore_event["type"] == "message_restored"
        assert restore_event["message"]["id"] == msg_id


def test_websocket_broadcast_to_multiple_clients(sync_client: TestClient):
    """Test that messages broadcast to all connected clients."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws1:
        ws1.receive_json()  # initial state

        with sync_client.websocket_connect("/ws?station=Station-2") as ws2:
            ws2.receive_json()  # initial state

            # Station 1 creates message
            ws1.send_json({
                "type": "create_message",
                "content": "Broadcast test"
            })

            # Both should receive broadcast
            event1 = ws1.receive_json()
            event2 = ws2.receive_json()

            assert event1["type"] == "message_created"
            assert event2["type"] == "message_created"
            assert event1["message"]["content"] == "Broadcast test"
            assert event2["message"]["content"] == "Broadcast test"


# =============================================================================
# WIPE/RESTORE VIA WEBSOCKET
# =============================================================================


def test_websocket_wipe_all(sync_client: TestClient):
    """Test wipe_all broadcasts delete events for each message."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Create some messages
        ws.send_json({"type": "create_message", "content": "First"})
        ws.receive_json()  # create event
        ws.send_json({"type": "create_message", "content": "Second"})
        ws.receive_json()  # create event

        # Wipe all
        ws.send_json({"type": "wipe_all"})

        # Should receive delete events for each message
        event1 = ws.receive_json()
        event2 = ws.receive_json()

        assert event1["type"] == "message_deleted"
        assert event2["type"] == "message_deleted"


def test_websocket_restore_wipe(sync_client: TestClient):
    """Test restore_wipe broadcasts restore events for each message."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Create and wipe
        ws.send_json({"type": "create_message", "content": "Test"})
        ws.receive_json()  # create event
        ws.send_json({"type": "wipe_all"})
        ws.receive_json()  # delete event

        # Restore
        ws.send_json({"type": "restore_wipe"})
        restore_event = ws.receive_json()

        assert restore_event["type"] == "message_restored"
        assert restore_event["message"]["content"] == "Test"


def test_websocket_wipe_empty(sync_client: TestClient):
    """Test wipe_all on empty database sends no events."""
    import select

    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        initial = ws.receive_json()
        assert initial["type"] == "initial_state"
        assert initial["messages"] == []

        # Wipe on empty
        ws.send_json({"type": "wipe_all"})

        # No events should be sent - we can't easily test "no message"
        # so we just verify no exception and the connection stays open
        # by sending another command that will respond
        ws.send_json({"type": "create_message", "content": "After wipe"})
        event = ws.receive_json()
        assert event["type"] == "message_created"


# =============================================================================
# ERROR HANDLING
# =============================================================================


def test_websocket_empty_content(sync_client: TestClient):
    """Test that empty content message is ignored."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Send empty content
        ws.send_json({"type": "create_message", "content": ""})

        # Should not receive a message_created event
        # Verify by sending a valid message and checking we only get one event
        ws.send_json({"type": "create_message", "content": "Valid"})
        event = ws.receive_json()

        assert event["type"] == "message_created"
        assert event["message"]["content"] == "Valid"


def test_websocket_invalid_message_id(sync_client: TestClient):
    """Test that invalid message_id doesn't crash the server."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Try to delete non-existent message
        ws.send_json({
            "type": "delete_message",
            "message_id": "nonexistent-uuid"
        })

        # Connection should stay open - verify by creating a message
        ws.send_json({"type": "create_message", "content": "Still works"})
        event = ws.receive_json()
        assert event["type"] == "message_created"


def test_websocket_invalid_direction(sync_client: TestClient):
    """Test that invalid direction is handled gracefully."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Create a message
        ws.send_json({"type": "create_message", "content": "Test"})
        create_event = ws.receive_json()
        msg_id = create_event["message"]["id"]

        # Try invalid direction
        ws.send_json({
            "type": "move_message",
            "message_id": msg_id,
            "direction": "invalid"
        })

        # Connection should stay open
        ws.send_json({"type": "create_message", "content": "Still works"})
        event = ws.receive_json()
        assert event["type"] == "message_created"


def test_websocket_unknown_event(sync_client: TestClient):
    """Test that unknown event type is ignored."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Send unknown event type
        ws.send_json({"type": "unknown_event", "data": "test"})

        # Connection should stay open
        ws.send_json({"type": "create_message", "content": "Still works"})
        event = ws.receive_json()
        assert event["type"] == "message_created"


# =============================================================================
# MULTI-CLIENT SCENARIOS
# =============================================================================


def test_websocket_duplicate_station_replaces(sync_client: TestClient):
    """Test that second connection with same station name replaces first."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws1:
        ws1.receive_json()  # initial state

        # Connect second client with same station name
        with sync_client.websocket_connect("/ws?station=Station-1") as ws2:
            ws2.receive_json()  # initial state

            # Create message from second connection
            ws2.send_json({"type": "create_message", "content": "From WS2"})
            event = ws2.receive_json()

            assert event["type"] == "message_created"
            assert event["message"]["station_name"] == "Station-1"


def test_websocket_multiple_stations_receive_broadcasts(sync_client: TestClient):
    """Test that all stations receive broadcasts correctly."""
    with sync_client.websocket_connect("/ws?station=Front-Desk") as ws1:
        ws1.receive_json()

        with sync_client.websocket_connect("/ws?station=Back-Office") as ws2:
            ws2.receive_json()

            with sync_client.websocket_connect("/ws?station=Hygiene") as ws3:
                ws3.receive_json()

                # Front-Desk creates message
                ws1.send_json({"type": "create_message", "content": "Patient ready"})

                # All three should receive
                e1 = ws1.receive_json()
                e2 = ws2.receive_json()
                e3 = ws3.receive_json()

                assert e1["type"] == "message_created"
                assert e2["type"] == "message_created"
                assert e3["type"] == "message_created"

                assert e1["message"]["station_name"] == "Front-Desk"
                assert e2["message"]["station_name"] == "Front-Desk"
                assert e3["message"]["station_name"] == "Front-Desk"


# =============================================================================
# INPUT VALIDATION
# =============================================================================


def test_websocket_station_name_too_long(sync_client: TestClient):
    """Test that station names > 255 chars are rejected."""
    long_name = "A" * 300
    with pytest.raises(Exception):
        with sync_client.websocket_connect(f"/ws?station={long_name}") as ws:
            pass


def test_websocket_station_name_control_chars(sync_client: TestClient):
    """Test that station names with control characters are rejected."""
    # Use URL-encoded newline (%0A) - server decodes it before validation
    with pytest.raises(Exception):
        with sync_client.websocket_connect("/ws?station=Test%0AStation") as ws:
            pass


def test_websocket_message_too_long(sync_client: TestClient):
    """Test that messages > 10000 chars are ignored."""
    with sync_client.websocket_connect("/ws?station=Station-1") as ws:
        ws.receive_json()  # initial state

        # Send oversized message
        ws.send_json({"type": "create_message", "content": "A" * 15000})

        # Should be ignored - verify by sending valid message and checking we only get one event
        ws.send_json({"type": "create_message", "content": "Valid message"})
        event = ws.receive_json()

        assert event["type"] == "message_created"
        assert event["message"]["content"] == "Valid message"
