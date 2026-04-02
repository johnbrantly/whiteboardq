"""Pydantic models for messages, config, and WebSocket events."""

from datetime import datetime
from typing import Literal, Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A message on the whiteboard."""

    id: str
    content: str
    station_name: str
    created_at: datetime
    position: int


class MessageCreate(BaseModel):
    """Request body for creating a message."""

    content: str = Field(..., min_length=1, max_length=10000)


class ServerConfig(BaseModel):
    """Server configuration for message thresholds and sounds."""

    yellow_threshold_minutes: int = 10
    red_threshold_minutes: int = 20
    overdue_threshold_minutes: int = 30

    # Sound settings (pushed to clients)
    sound_new_message: str = ""
    sound_yellow: str = "soft.wav"
    sound_red: str = "chimes.wav"
    sound_overdue: str = "littletrumpet.wav"


class WSEvent(BaseModel):
    """Base WebSocket event."""

    type: str


class InitialStateEvent(BaseModel):
    """Sent to client on connection."""

    type: Literal["initial_state"] = "initial_state"
    messages: list[Message]
    config: ServerConfig


class MessageCreatedEvent(BaseModel):
    """Broadcast when a message is created."""

    type: Literal["message_created"] = "message_created"
    message: Message


class PositionUpdate(BaseModel):
    """Position update for a single message."""

    id: str
    position: int


class MessageMovedEvent(BaseModel):
    """Broadcast when a message is moved."""

    type: Literal["message_moved"] = "message_moved"
    message_id: str
    new_position: int
    moved_by: str
    all_positions: list[PositionUpdate]


class MessageDeletedEvent(BaseModel):
    """Broadcast when a message is deleted."""

    type: Literal["message_deleted"] = "message_deleted"
    message_id: str
    deleted_by: str


class MessageRestoredEvent(BaseModel):
    """Broadcast when a message is restored."""

    type: Literal["message_restored"] = "message_restored"
    message: Message


class ConfigChangedEvent(BaseModel):
    """Broadcast when server config is updated."""

    type: Literal["config_changed"] = "config_changed"
    config: ServerConfig


# Client -> Server events
class CreateMessageRequest(BaseModel):
    """Client request to create a message."""

    type: Literal["create_message"] = "create_message"
    content: str


class MoveMessageRequest(BaseModel):
    """Client request to move a message."""

    type: Literal["move_message"] = "move_message"
    message_id: str
    direction: Literal["up", "down", "top"]


class DeleteMessageRequest(BaseModel):
    """Client request to delete a message."""

    type: Literal["delete_message"] = "delete_message"
    message_id: str


class RestoreMessageRequest(BaseModel):
    """Client request to restore a message."""

    type: Literal["restore_message"] = "restore_message"
    message_id: str
