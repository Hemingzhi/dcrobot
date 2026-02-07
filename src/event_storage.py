from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import List


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


@dataclass
class MultimediaItem:
    id: int
    guild_id: int
    media_type: str
    title: str
    provider_user_id: int
    created_at: str


@dataclass
class MultimediaView:
    id: int
    guild_id: int
    item_id: int
    viewer_user_id: int
    watched: int
    watched_at: str | None
    review: str | None
    created_at: str

@dataclass(frozen=True)
class IdTitle:
    id: int
    title: str

class EventStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            # --- events ---
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

            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(events);").fetchall()}

            if "remind_at_iso" not in existing_cols:
                conn.execute("ALTER TABLE events ADD COLUMN remind_at_iso TEXT;")

            if "reminded" not in existing_cols:
                conn.execute("ALTER TABLE events ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0;")

            if "remind_in_channel" not in existing_cols:
                conn.execute("ALTER TABLE events ADD COLUMN remind_in_channel INTEGER NOT NULL DEFAULT 1;")

            # --- category options ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_category_options (
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    PRIMARY KEY (guild_id, name)
                );
                """
            )

            # --- multimedia items (catalog) ---
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS multimedia_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,

                    media_type TEXT NOT NULL,
                    title TEXT NOT NULL,

                    provider_user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,

                    UNIQUE (guild_id, media_type, title)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mm_items_guild_type
                ON multimedia_items(guild_id, media_type);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mm_items_guild_created
                ON multimedia_items(guild_id, created_at);
                """
            )

            # --- multimedia views (per-user state) --- (NO FK)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS multimedia_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    guild_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,          -- logical ref to multimedia_items.id
                    viewer_user_id INTEGER NOT NULL,

                    watched INTEGER NOT NULL DEFAULT 0,
                    watched_at TEXT,
                    review TEXT,

                    created_at TEXT NOT NULL,

                    UNIQUE (guild_id, item_id, viewer_user_id)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mm_views_guild_item
                ON multimedia_views(guild_id, item_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mm_views_guild_viewer
                ON multimedia_views(guild_id, viewer_user_id);
                """
            )

            conn.commit()

    # -----------------------
    # category options
    # -----------------------
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
                WHERE guild_id = ? AND name = ?
                """,
                (guild_id, name),
            )
            conn.commit()
            return cur.rowcount

    # -----------------------
    # events
    # -----------------------
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
                LIMIT ?
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
                LIMIT ?
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
                WHERE expires_at <= ?
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
            cur = conn.execute("DELETE FROM events WHERE expires_at <= ?;", (now_iso,))
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
                WHERE id = ?
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
                LIMIT ?
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
            cur = conn.execute("UPDATE events SET reminded = 1 WHERE id = ?;", (event_id,))
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

    def get_multimedia_item_by_key(self, *, guild_id: int, media_type: str, title: str) -> MultimediaItem | None:
        media_type = (media_type or "").strip().lower()
        title = (title or "").strip()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, guild_id, media_type, title, provider_user_id, created_at
                FROM multimedia_items
                WHERE guild_id = ? AND media_type = ? AND title = ?
                LIMIT 1;
                """,
                (guild_id, media_type, title),
            ).fetchone()
        if row is None:
            return None
        return MultimediaItem(
            id=row[0],
            guild_id=row[1],
            media_type=row[2],
            title=row[3],
            provider_user_id=row[4],
            created_at=row[5],
        )

    def get_multimedia_item_by_id(self, *, guild_id: int, item_id: int) -> MultimediaItem | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, guild_id, media_type, title, provider_user_id, created_at
                FROM multimedia_items
                WHERE guild_id = ? AND id = ?
                LIMIT 1;
                """,
                (guild_id, int(item_id)),
            ).fetchone()
        if row is None:
            return None
        return MultimediaItem(
            id=row[0],
            guild_id=row[1],
            media_type=row[2],
            title=row[3],
            provider_user_id=row[4],
            created_at=row[5],
        )

    def create_or_get_multimedia_item(
        self,
        *,
        guild_id: int,
        provider_user_id: int,
        media_type: str,
        title: str,
        created_at: str | None = None,
    ) -> tuple[MultimediaItem, bool]:
        """
        Returns (item, created_new)
        """
        created_at = created_at or _utc_iso_now()
        media_type = (media_type or "").strip().lower()
        title = (title or "").strip()

        existing = self.get_multimedia_item_by_key(guild_id=guild_id, media_type=media_type, title=title)
        if existing is not None:
            return existing, False

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO multimedia_items (
                    guild_id, media_type, title, provider_user_id, created_at
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                (guild_id, media_type, title, provider_user_id, created_at),
            )
            conn.commit()
            item_id = cur.lastrowid

        return (
            MultimediaItem(
                id=item_id,
                guild_id=guild_id,
                media_type=media_type,
                title=title,
                provider_user_id=provider_user_id,
                created_at=created_at,
            ),
            True,
        )

    def list_multimedia_items(
        self,
        *,
        guild_id: int,
        media_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[MultimediaItem]:
        where = ["guild_id = ?"]
        params: list[object] = [guild_id]

        if media_type:
            where.append("media_type = ?")
            params.append(media_type.strip().lower())

        params.extend([int(limit), int(offset)])

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, guild_id, media_type, title, provider_user_id, created_at
                FROM multimedia_items
                WHERE {" AND ".join(where)}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                params,
            ).fetchall()

        return [
            MultimediaItem(
                id=r[0],
                guild_id=r[1],
                media_type=r[2],
                title=r[3],
                provider_user_id=r[4],
                created_at=r[5],
            )
            for r in rows
        ]

    def update_multimedia_item(
        self,
        *,
        guild_id: int,
        item_id: int,
        media_type: str | None = None,
        title: str | None = None,
    ) -> int:
        fields = []
        values: list[object] = []

        if media_type is not None:
            fields.append("media_type = ?")
            values.append(media_type.strip().lower())

        if title is not None:
            fields.append("title = ?")
            values.append(title.strip())

        if not fields:
            return 0

        values.extend([guild_id, int(item_id)])

        with self._connect() as conn:
            cur = conn.execute(
                f"""
                UPDATE multimedia_items
                SET {", ".join(fields)}
                WHERE guild_id = ? AND id = ?;
                """,
                values,
            )
            conn.commit()
            return cur.rowcount

    def delete_multimedia_item(self, *, guild_id: int, item_id: int) -> tuple[int, int]:
        """
        No FK: manual cascade delete.
        Returns (deleted_views, deleted_items)
        """
        with self._connect() as conn:
            cur_views = conn.execute(
                """
                DELETE FROM multimedia_views
                WHERE guild_id = ? AND item_id = ?;
                """,
                (guild_id, int(item_id)),
            )
            cur_item = conn.execute(
                """
                DELETE FROM multimedia_items
                WHERE guild_id = ? AND id = ?;
                """,
                (guild_id, int(item_id)),
            )
            conn.commit()
            return cur_views.rowcount, cur_item.rowcount

    def upsert_multimedia_view(
        self,
        *,
        guild_id: int,
        item_id: int,
        viewer_user_id: int,
        watched: int,
        watched_at: str | None = None,
        review: str | None = None,
        created_at: str | None = None,
    ) -> int:
        created_at = created_at or _utc_iso_now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO multimedia_views (
                    guild_id, item_id, viewer_user_id,
                    watched, watched_at, review, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, item_id, viewer_user_id) DO UPDATE SET
                    watched = excluded.watched,
                    watched_at = excluded.watched_at,
                    review = excluded.review;
                """,
                (
                    guild_id,
                    int(item_id),
                    int(viewer_user_id),
                    int(watched),
                    watched_at,
                    review,
                    created_at,
                ),
            )
            conn.commit()
            return cur.rowcount

    def delete_multimedia_view(self, *, guild_id: int, item_id: int, viewer_user_id: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM multimedia_views
                WHERE guild_id = ? AND item_id = ? AND viewer_user_id = ?;
                """,
                (guild_id, int(item_id), int(viewer_user_id)),
            )
            conn.commit()
            return cur.rowcount

    def list_my_multimedia(
        self,
        *,
        guild_id: int,
        viewer_user_id: int,
        watched: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[tuple[MultimediaItem, MultimediaView]]:
        where = ["v.guild_id = ?", "v.viewer_user_id = ?"]
        params: list[object] = [guild_id, int(viewer_user_id)]

        if watched is not None:
            where.append("v.watched = ?")
            params.append(int(watched))

        params.extend([int(limit), int(offset)])

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    i.id, i.guild_id, i.media_type, i.title, i.provider_user_id, i.created_at,
                    v.id, v.guild_id, v.item_id, v.viewer_user_id, v.watched, v.watched_at, v.review, v.created_at
                FROM multimedia_views v
                JOIN multimedia_items i
                  ON i.id = v.item_id AND i.guild_id = v.guild_id
                WHERE {" AND ".join(where)}
                ORDER BY COALESCE(v.watched_at, v.created_at) DESC, v.id DESC
                LIMIT ? OFFSET ?;
                """,
                params,
            ).fetchall()

        out: list[tuple[MultimediaItem, MultimediaView]] = []
        for r in rows:
            item = MultimediaItem(
                id=r[0],
                guild_id=r[1],
                media_type=r[2],
                title=r[3],
                provider_user_id=r[4],
                created_at=r[5],
            )
            view = MultimediaView(
                id=r[6],
                guild_id=r[7],
                item_id=r[8],
                viewer_user_id=r[9],
                watched=r[10],
                watched_at=r[11],
                review=r[12],
                created_at=r[13],
            )
            out.append((item, view))
        return out

    def list_multimedia_item_views(
        self,
        *,
        guild_id: int,
        item_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MultimediaView]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, guild_id, item_id, viewer_user_id, watched, watched_at, review, created_at
                FROM multimedia_views
                WHERE guild_id = ? AND item_id = ?
                ORDER BY COALESCE(watched_at, created_at) DESC, id DESC
                LIMIT ? OFFSET ?;
                """,
                (guild_id, int(item_id), int(limit), int(offset)),
            ).fetchall()

        return [
            MultimediaView(
                id=r[0],
                guild_id=r[1],
                item_id=r[2],
                viewer_user_id=r[3],
                watched=r[4],
                watched_at=r[5],
                review=r[6],
                created_at=r[7],
            )
            for r in rows
        ]

    def list_multimedia_items_for_user(
        self,
        *,
        guild_id: int,
        user_id: int,
        limit: int = 25,
    ) -> list[IdTitle]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title
                FROM multimedia_items
                WHERE guild_id = ? AND user_id = ?
                ORDER BY id DESC
                LIMIT ?;
                """,
                (guild_id, user_id, int(limit)),
            ).fetchall()

        return [IdTitle(id=int(r[0]), title=str(r[1])) for r in rows]
    
    def mark_multimedia_item_watched(
        self,
        *,
        guild_id: int,
        user_id: int,
        item_id: int,
        review: str | None,
    ) -> bool:
        """Mark watched=1 and persist review ('-' if empty). Returns True if updated."""
        final_review = (review or "").strip() or "-"

        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE multimedia_items
                SET watched = 1,
                    review = ?
                WHERE guild_id = ? AND user_id = ? AND id = ?;
                """,
                (final_review, guild_id, user_id, int(item_id)),
            )
            conn.commit()
            return cur.rowcount > 0