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

    remind_at_iso: str | None = None
    reminded: int = 0
    remind_in_channel: int = 1

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

            existing_cols = {
                r[1] for r in conn.execute("PRAGMA table_info(events);").fetchall()
            }

            if "remind_at_iso" not in existing_cols:
                conn.execute("ALTER TABLE events ADD COLUMN remind_at_iso TEXT;")

            if "reminded" not in existing_cols:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0;"
                )

            if "remind_in_channel" not in existing_cols:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN remind_in_channel INTEGER NOT NULL DEFAULT 1;"
                )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_category_options (
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    PRIMARY KEY (guild_id, name)
                );
                """
            )

            conn.commit()

    def list_category_options(self, *, guild_id: int, limit: int = 25) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM event_category_options
                WHERE guild_id = ?
                ORDER BY name ASC
                LIMIT ?;
                """,
                (guild_id, limit),
            ).fetchall()
        return [r[0] for r in rows]

    def list_all_category_options(self, *, guild_id: int, limit: int = 200) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM event_category_options
                WHERE guild_id = ?
                ORDER BY name ASC
                LIMIT ?;
                """,
                (guild_id, limit),
            ).fetchall()
        return [r[0] for r in rows]

    def add_category_option(self, *, guild_id: int, name: str) -> None:
        name = (name or "").strip()
        if not name:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO event_category_options (guild_id, name)
                VALUES (?, ?);
                """,
                (guild_id, name),
            )
            conn.commit()

    def has_category_option(self, *, guild_id: int, name: str) -> bool:
        name = (name or "").strip()
        if not name:
            return False
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM event_category_options
                WHERE guild_id = ? AND name = ?
                LIMIT 1;
                """,
                (guild_id, name),
            ).fetchone()
        return row is not None

    def delete_category_option(self, *, guild_id: int, name: str) -> int:
        name = (name or "").strip()
        if not name:
            return 0
        with self._connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM event_category_options
                WHERE guild_id = ? AND name = ?;
                """,
                (guild_id, name),
            )
            conn.commit()
            return cur.rowcount

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
                       description, created_by, expires_at, channel_name, member_limit,
                       remind_at_iso, reminded, remind_in_channel
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
                remind_at_iso=r[11],
                reminded=r[12],
                remind_in_channel=r[13],
            )
            for r in rows
        ]

    def list_events_for_day(
        self,
        *,
        guild_id: int,
        day_start_iso: str,
        day_end_iso: str,
        now_iso: str,
        limit: int = 50,
    ) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                       description, created_by, expires_at, channel_name, member_limit,
                       remind_at_iso, reminded, remind_in_channel
                FROM events
                WHERE guild_id = ?
                  AND expires_at > ?
                  AND start_iso >= ?
                  AND start_iso < ?
                ORDER BY start_iso ASC
                LIMIT ?;
                """,
                (guild_id, now_iso, day_start_iso, day_end_iso, limit),
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
                remind_at_iso=r[11],
                reminded=r[12],
                remind_in_channel=r[13],
            )
            for r in rows
        ]

    def fetch_expired_events(self, now_iso: str) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                       description, created_by, expires_at, channel_name, member_limit,
                       remind_at_iso, reminded, remind_in_channel
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
                remind_at_iso=r[11],
                reminded=r[12],
                remind_in_channel=r[13],
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

    def set_event_reminder(
        self,
        *,
        event_id: int,
        remind_at_iso: str,
        remind_in_channel: bool = True,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE events
                SET remind_at_iso = ?, reminded = 0, remind_in_channel = ?
                WHERE id = ?;
                """,
                (remind_at_iso, 1 if remind_in_channel else 0, event_id),
            )
            conn.commit()
            return cur.rowcount

    def fetch_due_reminders(
        self,
        *,
        now_iso: str,
        limit: int = 50,
    ) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                       description, created_by, expires_at, channel_name, member_limit,
                       remind_at_iso, reminded, remind_in_channel
                FROM events
                WHERE remind_at_iso IS NOT NULL
                  AND reminded = 0
                  AND remind_at_iso <= ?
                  AND expires_at > ?
                ORDER BY remind_at_iso ASC
                LIMIT ?;
                """,
                (now_iso, now_iso, limit),
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
                remind_at_iso=r[11],
                reminded=r[12],
                remind_in_channel=r[13],
            )
            for r in rows
        ]

    def mark_event_reminded(self, *, event_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE events SET reminded = 1 WHERE id = ?;",
                (event_id,),
            )
            conn.commit()
            return cur.rowcount

    def get_event_by_id(self, *, event_id: int) -> Event | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                    description, created_by, expires_at, channel_name, member_limit,
                    remind_at_iso, reminded, remind_in_channel
                FROM events
                WHERE id = ?
                LIMIT 1;
                """,
                (event_id,),
            ).fetchone()

        if row is None:
            return None

        return Event(
            id=row[0],
            guild_id=row[1],
            channel_id=row[2],
            title=row[3],
            start_iso=row[4],
            end_iso=row[5],
            description=row[6],
            created_by=row[7],
            expires_at=row[8],
            channel_name=row[9],
            member_limit=row[10],
            remind_at_iso=row[11],
            reminded=row[12],
            remind_in_channel=row[13],
        )

    def cancel_event_reminder(self, *, event_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE events
                SET remind_at_iso = NULL, reminded = 0
                WHERE id = ?;
                """,
                (event_id,),
            )
            conn.commit()
            return cur.rowcount

    def list_pending_reminders(self, *, guild_id: int, now_iso: str, limit: int = 20) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, channel_id, title, start_iso, end_iso,
                    description, created_by, expires_at, channel_name, member_limit,
                    remind_at_iso, reminded, remind_in_channel
                FROM events
                WHERE guild_id = ?
                AND remind_at_iso IS NOT NULL
                AND reminded = 0
                AND expires_at > ?
                AND remind_at_iso >= ?
                ORDER BY remind_at_iso ASC
                LIMIT ?;
                """,
                (guild_id, now_iso, now_iso, limit),
            ).fetchall()

        return [
            Event(
                id=r[0], guild_id=r[1], channel_id=r[2], title=r[3],
                start_iso=r[4], end_iso=r[5], description=r[6], created_by=r[7],
                expires_at=r[8], channel_name=r[9], member_limit=r[10],
                remind_at_iso=r[11], reminded=r[12], remind_in_channel=r[13],
            )
            for r in rows
        ]
