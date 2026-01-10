from dataclasses import dataclass
import sqlite3
from pathlib import Path
from typing import List


@dataclass
class Event:
    id: int
    guild_id: int
    channel_id: int          
    title: str
    start_iso: str
    end_iso: str | None
    description: str | None
    created_by: int
    expires_at: str
    channel_name: str | None 
    member_limit: int | None  

class EventStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
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
                    channel_name TEXT,
                    member_limit INTEGER
                );
                """
            )
            conn.commit()

    def create_event(
        self,
        *,
        guild_id: int,
        channel_id: int,
        title: str,
        start_iso: str,
        end_iso: str | None,
        description: str | None,
        created_by: int,
        expires_at: str,
        channel_name: str | None,
        member_limit: int | None,
    ) -> Event:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO events (
                    guild_id, channel_id, title, start_iso, end_iso,
                    description, created_by, expires_at, channel_name, member_limit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    channel_id,
                    title,
                    start_iso,
                    end_iso,
                    description,
                    created_by,
                    expires_at,
                    channel_name,
                    member_limit,
                ),
            )
            conn.commit()
            event_id = cur.lastrowid

        return Event(
            id=event_id,
            guild_id=guild_id,
            channel_id=channel_id,
            title=title,
            start_iso=start_iso,
            end_iso=end_iso,
            description=description,
            created_by=created_by,
            expires_at=expires_at,
            channel_name=channel_name,
            member_limit=member_limit,
        )

    def list_active_events(
        self,
        *,
        guild_id: int,
        channel_id: int,
        now_iso: str,
        limit: int = 20,
    ) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                       description, created_by, expires_at, channel_name, member_limit
                FROM events
                WHERE guild_id = ?
                  AND channel_id = ?
                  AND expires_at > ?
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
                channel_name=r[9],
                member_limit=r[10],
            )
            for r in rows
        ]

    def fetch_expired_events(self, now_iso: str) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                       description, created_by, expires_at, channel_name, member_limit
                FROM events
                WHERE expires_at <= ?;
                """,
                (now_iso,),
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
                channel_name=r[9],
                member_limit=r[10],
            )
            for r in rows
        ]

    def delete_expired(self, now_iso: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM events WHERE expires_at <= ?;",
                (now_iso,),
            )
            conn.commit()
            return cur.rowcount
