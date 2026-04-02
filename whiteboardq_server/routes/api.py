"""REST API endpoints for messages and server configuration."""

import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Header, Query, Request

from .. import database
from ..models import (
    Message,
    MessageCreate,
    ServerConfig,
    MessageCreatedEvent,
    MessageMovedEvent,
    MessageDeletedEvent,
    MessageRestoredEvent,
    ConfigChangedEvent,
)
from ..websocket_manager import manager

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint with actual checks."""
    checks = {"database": "ok"}

    # Check database connectivity
    try:
        await database.db.get_config()
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Report connected clients
    checks["connected_clients"] = len(manager.connected_stations)

    # Calculate uptime
    start_time = getattr(request.app.state, "start_time", None)
    uptime_seconds = int(time.time() - start_time) if start_time else 0

    # Overall status
    all_ok = checks["database"] == "ok"

    return {
        "status": "ok" if all_ok else "degraded",
        "uptime_seconds": uptime_seconds,
        "checks": checks,
    }


@router.get("/api/messages", response_model=list[Message])
async def get_messages():
    """Get all active messages ordered by position."""
    return await database.db.get_messages()


@router.post("/api/messages", response_model=Message, status_code=201)
async def create_message(
    body: MessageCreate,
    x_station_name: str = Header(..., alias="X-Station-Name"),
):
    """Create a new message."""
    message = await database.db.create_message(body.content, x_station_name)

    # Broadcast to all WebSocket clients
    event = MessageCreatedEvent(message=message)
    await manager.broadcast(event.model_dump(mode="json"))

    return message


@router.put("/api/messages/{message_id}/move", response_model=dict)
async def move_message(
    message_id: str,
    direction: Literal["up", "down", "top"] = Query(...),
    x_station_name: str = Header(..., alias="X-Station-Name"),
):
    """Move a message up, down, or to top."""
    result = await database.db.move_message(message_id, direction, x_station_name)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found")

    new_position, all_positions = result

    # Broadcast to all WebSocket clients
    event = MessageMovedEvent(
        message_id=message_id,
        new_position=new_position,
        moved_by=x_station_name,
        all_positions=all_positions,
    )
    await manager.broadcast(event.model_dump(mode="json"))

    return {"message_id": message_id, "new_position": new_position}


@router.delete("/api/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: str,
    x_station_name: str = Header(..., alias="X-Station-Name"),
):
    """Soft delete a message."""
    message = await database.db.delete_message(message_id, x_station_name)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")

    # Broadcast to all WebSocket clients
    event = MessageDeletedEvent(message_id=message_id, deleted_by=x_station_name)
    await manager.broadcast(event.model_dump(mode="json"))

    return None


@router.post("/api/messages/{message_id}/restore", response_model=Message)
async def restore_message(
    message_id: str,
    x_station_name: str = Header(..., alias="X-Station-Name"),
):
    """Restore a soft-deleted message."""
    message = await database.db.restore_message(message_id, x_station_name)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found or not deleted")

    # Broadcast to all WebSocket clients
    event = MessageRestoredEvent(message=message)
    await manager.broadcast(event.model_dump(mode="json"))

    return message


@router.get("/api/config", response_model=ServerConfig)
async def get_config():
    """Get server configuration (thresholds)."""
    return await database.db.get_config()


@router.put("/api/config", response_model=ServerConfig)
async def update_config(config: ServerConfig):
    """Update server configuration (thresholds and sounds)."""
    await database.db.set_config(config)

    # Broadcast to all connected clients
    event = ConfigChangedEvent(config=config)
    await manager.broadcast(event.model_dump(mode="json"))

    return config
