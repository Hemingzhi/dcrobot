from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass(frozen=True)
class Event:
    id: int
    guild_id: int
    channel_id: int
    title: str
    start_iso: str
    end_iso: Optional[str]
    description: Optional[str]
    created_by: int
    expires_at: str


class EventStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    start_iso TEXT NOT NULL,
                    end_iso TEXT,
                    description TEXT,
                    created_by INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_expires_at ON events(expires_at);")

    def create_event(
        self,
        *,
        guild_id: int,
        channel_id: int,
        title: str,
        start_iso: str,
        end_iso: Optional[str],
        description: Optional[str],
        created_by: int,
        expires_at: str,
    ) -> Event:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO events (guild_id, channel_id, title, start_iso, end_iso, description, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (guild_id, channel_id, title, start_iso, end_iso, description, created_by, expires_at),
            )
            event_id = int(cur.lastrowid)

        return Event(
            id=event_id,
            guild_id=guild_id,
            channel_id=channel_id,
            title=title,
            start_iso=start_iso,
            end_iso=end_iso,
            description=description,
            created_by=created_by,
        )

    def delete_expired(self, now_iso: str) -> int:
        """Delete expired events. Return number of deleted rows."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM events WHERE expires_at <= ?;", (now_iso,))
            return int(cur.rowcount)
        
    def list_active_events(self, *, guild_id: int, channel_id: int, now_iso: str, limit: int = 20) -> list[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso, description, created_by, expires_at
                FROM events
                WHERE guild_id = ? AND channel_id = ? AND expires_at > ?
                ORDER BY start_iso ASC
                LIMIT ?;
                """,
                (guild_id, channel_id, now_iso, limit),
            ).fetchall()

        return [
            Event(
                id=r[0],
                guild_id=r[1],
                channel_id=r[2],
                title=r[3],
                start_iso=r[4],
                end_iso=r[5],
                description=r[6],
                created_by=r[7],
                expires_at=r[8],
            )
            for r in rows
        ]