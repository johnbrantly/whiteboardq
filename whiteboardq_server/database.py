"""Async SQLite database layer for messages, history, and config."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from .config import config
from .models import Message, ServerConfig, PositionUpdate


class Database:
    """Async SQLite database operations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Open database connection."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON")

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the active connection."""
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    async def init_db(self) -> None:
        """Initialize database schema."""
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                station_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                position INTEGER NOT NULL,
                deleted_at TEXT,
                deleted_by TEXT
            );

            CREATE TABLE IF NOT EXISTS message_history (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_station TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS server_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_active
                ON messages(deleted_at) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_messages_position
                ON messages(position);

            CREATE TABLE IF NOT EXISTS _system (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        await self.conn.commit()

    async def _log_history(
        self,
        message_id: str,
        action: str,
        actor_station: str,
        details: Optional[dict] = None,
    ) -> None:
        """Log an action to message_history."""
        await self.conn.execute(
            """
            INSERT INTO message_history (id, message_id, action, actor_station, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                message_id,
                action,
                actor_station,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(details) if details else None,
            ),
        )

    async def create_message(self, content: str, station_name: str) -> Message:
        """Create a new message."""
        message_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        # Get next position (max + 1, or 1 if no messages)
        cursor = await self.conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM messages WHERE deleted_at IS NULL"
        )
        row = await cursor.fetchone()
        position = row[0]

        await self.conn.execute(
            """
            INSERT INTO messages (id, content, station_name, created_at, position)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, content, station_name, created_at.isoformat(), position),
        )

        await self._log_history(message_id, "created", station_name)
        await self.conn.commit()

        return Message(
            id=message_id,
            content=content,
            station_name=station_name,
            created_at=created_at,
            position=position,
        )

    async def get_messages(self) -> list[Message]:
        """Get all active messages ordered by position."""
        cursor = await self.conn.execute(
            """
            SELECT id, content, station_name, created_at, position
            FROM messages
            WHERE deleted_at IS NULL
            ORDER BY position ASC
            """
        )
        rows = await cursor.fetchall()
        return [
            Message(
                id=row["id"],
                content=row["content"],
                station_name=row["station_name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                position=row["position"],
            )
            for row in rows
        ]

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a single message by ID."""
        cursor = await self.conn.execute(
            """
            SELECT id, content, station_name, created_at, position
            FROM messages
            WHERE id = ? AND deleted_at IS NULL
            """,
            (message_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Message(
            id=row["id"],
            content=row["content"],
            station_name=row["station_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            position=row["position"],
        )

    async def move_message(
        self, message_id: str, direction: str, actor_station: str
    ) -> Optional[tuple[int, list[PositionUpdate]]]:
        """
        Move a message up, down, or to top.
        Returns (new_position, all_position_updates) or None if message not found.
        """
        message = await self.get_message(message_id)
        if not message:
            return None

        messages = await self.get_messages()
        positions = {m.id: m.position for m in messages}
        sorted_messages = sorted(messages, key=lambda m: m.position)

        current_idx = next(
            (i for i, m in enumerate(sorted_messages) if m.id == message_id), None
        )
        if current_idx is None:
            return None

        updates: list[PositionUpdate] = []

        if direction == "up" and current_idx > 0:
            # Swap position integers with the adjacent message above.
            # Both messages exchange their position values so ordering flips.
            other = sorted_messages[current_idx - 1]
            new_pos = other.position
            other_new_pos = message.position

            await self.conn.execute(
                "UPDATE messages SET position = ? WHERE id = ?",
                (new_pos, message_id),
            )
            await self.conn.execute(
                "UPDATE messages SET position = ? WHERE id = ?",
                (other_new_pos, other.id),
            )
            updates = [
                PositionUpdate(id=message_id, position=new_pos),
                PositionUpdate(id=other.id, position=other_new_pos),
            ]
            new_position = new_pos

        elif direction == "down" and current_idx < len(sorted_messages) - 1:
            # Swap position integers with the adjacent message below.
            other = sorted_messages[current_idx + 1]
            new_pos = other.position
            other_new_pos = message.position

            await self.conn.execute(
                "UPDATE messages SET position = ? WHERE id = ?",
                (new_pos, message_id),
            )
            await self.conn.execute(
                "UPDATE messages SET position = ? WHERE id = ?",
                (other_new_pos, other.id),
            )
            updates = [
                PositionUpdate(id=message_id, position=new_pos),
                PositionUpdate(id=other.id, position=other_new_pos),
            ]
            new_position = new_pos

        elif direction == "top" and current_idx > 0:
            # Assign position = min_position - 1 to jump to top.
            # Avoids reindexing all other messages; positions may go negative over time.
            min_pos = sorted_messages[0].position
            new_pos = min_pos - 1

            await self.conn.execute(
                "UPDATE messages SET position = ? WHERE id = ?",
                (new_pos, message_id),
            )
            updates = [PositionUpdate(id=message_id, position=new_pos)]
            new_position = new_pos
        else:
            # Already at boundary (top for up, bottom for down) — no-op
            new_position = message.position
            updates = []

        if updates:
            await self._log_history(
                message_id,
                "moved",
                actor_station,
                {"direction": direction, "new_position": new_position},
            )
            await self.conn.commit()

        return new_position, updates

    async def delete_message(
        self, message_id: str, actor_station: str
    ) -> Optional[Message]:
        """Soft delete a message. Returns the message if found."""
        message = await self.get_message(message_id)
        if not message:
            return None

        deleted_at = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            UPDATE messages
            SET deleted_at = ?, deleted_by = ?
            WHERE id = ?
            """,
            (deleted_at, actor_station, message_id),
        )

        await self._log_history(message_id, "deleted", actor_station)
        await self.conn.commit()

        return message

    async def wipe_all_messages(self, actor_station: str) -> list[str]:
        """Soft delete all active messages. Returns list of deleted message IDs."""
        # Get all active message IDs first
        cursor = await self.conn.execute(
            "SELECT id FROM messages WHERE deleted_at IS NULL"
        )
        rows = await cursor.fetchall()
        message_ids = [row["id"] for row in rows]

        if not message_ids:
            return []

        deleted_at = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            UPDATE messages
            SET deleted_at = ?, deleted_by = ?
            WHERE deleted_at IS NULL
            """,
            (deleted_at, actor_station),
        )

        # Log history for each message
        for message_id in message_ids:
            await self._log_history(message_id, "deleted", actor_station)

        await self.conn.commit()

        # Store for potential restore (persisted to survive restart)
        await self.set_system_value("last_wipe_ids", json.dumps(message_ids))
        return message_ids

    async def restore_last_wipe(self, actor_station: str) -> list[Message]:
        """Restore messages from the last wipe_all. Returns restored messages."""
        wipe_ids_json = await self.get_system_value("last_wipe_ids")
        if not wipe_ids_json:
            return []

        wipe_ids = json.loads(wipe_ids_json)
        if not wipe_ids:
            return []

        restored_messages = []
        for message_id in wipe_ids:
            message = await self.restore_message(message_id, actor_station)
            if message:
                restored_messages.append(message)

        # Clear the stored wipe IDs
        await self.set_system_value("last_wipe_ids", "")
        return restored_messages

    async def has_wipe_to_restore(self) -> bool:
        """Check if there's a wipe that can be restored."""
        wipe_ids_json = await self.get_system_value("last_wipe_ids")
        if not wipe_ids_json:
            return False
        wipe_ids = json.loads(wipe_ids_json)
        return bool(wipe_ids)

    async def restore_message(
        self, message_id: str, actor_station: str
    ) -> Optional[Message]:
        """Restore a soft-deleted message."""
        # Check if message exists and is deleted
        cursor = await self.conn.execute(
            """
            SELECT id, content, station_name, created_at, position
            FROM messages
            WHERE id = ? AND deleted_at IS NOT NULL
            """,
            (message_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Get new position (at bottom)
        pos_cursor = await self.conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM messages WHERE deleted_at IS NULL"
        )
        pos_row = await pos_cursor.fetchone()
        new_position = pos_row[0]

        await self.conn.execute(
            """
            UPDATE messages
            SET deleted_at = NULL, deleted_by = NULL, position = ?
            WHERE id = ?
            """,
            (new_position, message_id),
        )

        await self._log_history(message_id, "restored", actor_station)
        await self.conn.commit()

        return Message(
            id=row["id"],
            content=row["content"],
            station_name=row["station_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            position=new_position,
        )

    async def get_config(self) -> ServerConfig:
        """Get server configuration."""
        cursor = await self.conn.execute("SELECT key, value FROM server_config")
        rows = await cursor.fetchall()
        config_dict = {row["key"]: row["value"] for row in rows}

        return ServerConfig(
            yellow_threshold_minutes=int(
                config_dict.get("yellow_threshold_minutes", 10)
            ),
            red_threshold_minutes=int(config_dict.get("red_threshold_minutes", 20)),
            overdue_threshold_minutes=int(
                config_dict.get("overdue_threshold_minutes", 30)
            ),
            sound_new_message=config_dict.get("sound_new_message", ""),
            sound_yellow=config_dict.get("sound_yellow", "soft.wav"),
            sound_red=config_dict.get("sound_red", "chimes.wav"),
            sound_overdue=config_dict.get("sound_overdue", "littletrumpet.wav"),
        )

    async def set_config(self, server_config: ServerConfig) -> None:
        """Update server configuration."""
        for key, value in server_config.model_dump().items():
            await self.conn.execute(
                """
                INSERT INTO server_config (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )
        await self.conn.commit()

    async def get_system_value(self, key: str) -> Optional[str]:
        """Get a value from the _system table."""
        cursor = await self.conn.execute(
            "SELECT value FROM _system WHERE key = ?",
            (key,),
        )
        row = await cursor.fetchone()
        return row["value"] if row else None

    async def set_system_value(self, key: str, value: str) -> None:
        """Set a value in the _system table."""
        await self.conn.execute(
            """
            INSERT INTO _system (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await self.conn.commit()


# Global database instance
db = Database()
