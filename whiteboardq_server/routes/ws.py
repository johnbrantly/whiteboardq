"""WebSocket endpoint — handles real-time client messaging."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .. import database
from ..models import (
    InitialStateEvent,
    MessageCreatedEvent,
    MessageMovedEvent,
    MessageDeletedEvent,
    MessageRestoredEvent,
)
from ..websocket_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def handle_create_message(data: dict[str, Any], station_name: str) -> None:
    """Handle create_message event from client."""
    content = data.get("content", "").strip()
    if not content:
        logger.debug(f"Empty message content from {station_name}")
        return

    if len(content) > 10000:
        logger.debug(f"Message too long from {station_name}: {len(content)} chars")
        return

    message = await database.db.create_message(content, station_name)
    event = MessageCreatedEvent(message=message)
    await manager.broadcast(event.model_dump(mode="json"))


async def handle_move_message(data: dict[str, Any], station_name: str) -> None:
    """Handle move_message event from client."""
    message_id = data.get("message_id")
    direction = data.get("direction")

    if not message_id or direction not in ("up", "down", "top"):
        logger.debug(f"Invalid move request from {station_name}: {data}")
        return

    result = await database.db.move_message(message_id, direction, station_name)
    if result is None:
        logger.debug(f"Message not found for move: {message_id}")
        return

    new_position, all_positions = result
    event = MessageMovedEvent(
        message_id=message_id,
        new_position=new_position,
        moved_by=station_name,
        all_positions=all_positions,
    )
    await manager.broadcast(event.model_dump(mode="json"))


async def handle_delete_message(data: dict[str, Any], station_name: str) -> None:
    """Handle delete_message event from client."""
    message_id = data.get("message_id")
    if not message_id:
        logger.debug(f"Missing message_id in delete request from {station_name}")
        return

    message = await database.db.delete_message(message_id, station_name)
    if message is None:
        logger.debug(f"Message not found for delete: {message_id}")
        return

    event = MessageDeletedEvent(message_id=message_id, deleted_by=station_name)
    await manager.broadcast(event.model_dump(mode="json"))


async def handle_restore_message(data: dict[str, Any], station_name: str) -> None:
    """Handle restore_message event from client."""
    message_id = data.get("message_id")
    if not message_id:
        logger.debug(f"Missing message_id in restore request from {station_name}")
        return

    message = await database.db.restore_message(message_id, station_name)
    if message is None:
        logger.debug(f"Message not found for restore: {message_id}")
        return

    event = MessageRestoredEvent(message=message)
    await manager.broadcast(event.model_dump(mode="json"))


async def handle_wipe_all(data: dict[str, Any], station_name: str) -> None:
    """Handle wipe_all event - delete all messages."""
    message_ids = await database.db.wipe_all_messages(station_name)
    logger.info(f"Wiped {len(message_ids)} messages by {station_name}")

    # Broadcast deletion for each message
    for message_id in message_ids:
        event = MessageDeletedEvent(message_id=message_id, deleted_by=station_name)
        await manager.broadcast(event.model_dump(mode="json"))


async def handle_restore_wipe(data: dict[str, Any], station_name: str) -> None:
    """Handle restore_wipe event - restore messages from last wipe."""
    if not await database.db.has_wipe_to_restore():
        logger.debug(f"No wipe to restore for {station_name}")
        return

    restored_messages = await database.db.restore_last_wipe(station_name)
    logger.info(f"Restored {len(restored_messages)} messages by {station_name}")

    # Broadcast restoration for each message
    for message in restored_messages:
        event = MessageRestoredEvent(message=message)
        await manager.broadcast(event.model_dump(mode="json"))


# Event handlers mapping
EVENT_HANDLERS = {
    "create_message": handle_create_message,
    "move_message": handle_move_message,
    "delete_message": handle_delete_message,
    "restore_message": handle_restore_message,
    "wipe_all": handle_wipe_all,
    "restore_wipe": handle_restore_wipe,
}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    station: str = Query(...),
):
    """WebSocket endpoint for real-time messaging."""
    station_name = station.strip()
    if not station_name:
        await websocket.close(code=1008, reason="Station name required")
        return

    # Validate station name length
    if len(station_name) > 255:
        await websocket.close(code=1008, reason="Station name too long")
        return

    # Validate station name characters (printable, no control chars)
    if not all(c.isprintable() and c not in '\n\r\t' for c in station_name):
        await websocket.close(code=1008, reason="Invalid characters in station name")
        return

    await manager.connect(websocket, station_name)

    try:
        # Send initial state
        messages = await database.db.get_messages()
        config = await database.db.get_config()

        initial_event = InitialStateEvent(
            messages=messages, config=config,
        )
        await websocket.send_json(initial_event.model_dump(mode="json"))

        # Message loop
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type in EVENT_HANDLERS:
                await EVENT_HANDLERS[event_type](data, station_name)
            else:
                logger.debug(f"Unknown event type from {station_name}: {event_type}")

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {station_name}")
    except Exception as e:
        logger.exception(f"WebSocket error for {station_name}: {e}")
    finally:
        manager.disconnect(station_name)
