from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import tasks

logger = logging.getLogger(__name__)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReminderScheduler:
    """
    轮询 DB，发送到点提醒。
    依赖 store 方法：
      - fetch_due_reminders(now_iso=..., limit=...)
      - mark_event_reminded(event_id=...)
    """

    def __init__(self, client: discord.Client, poll_seconds: int = 15):
        self.client = client
        self.poll_seconds = max(5, min(int(poll_seconds), 60))

        self._poll_due.change_interval(seconds=self.poll_seconds)

    def start(self) -> None:
        if not self._poll_due.is_running():
            self._poll_due.start()

    def stop(self) -> None:
        if self._poll_due.is_running():
            self._poll_due.cancel()

    @tasks.loop(seconds=15) 
    async def _poll_due(self):
        await self._run_once()

    @_poll_due.before_loop
    async def _before(self):
        await self.client.wait_until_ready()
        logger.info("ReminderScheduler started (poll_seconds=%s)", self.poll_seconds)

    async def _run_once(self):
        store = getattr(self.client, "store", None)
        if store is None:
            return

        now_iso = now_utc_iso()

        try:
            due_events = store.fetch_due_reminders(now_iso=now_iso, limit=50)
        except Exception:
            logger.exception("fetch_due_reminders failed")
            return

        for ev in due_events:
            sent = await self._send_one(ev)
            if sent:
                try:
                    store.mark_event_reminded(event_id=ev.id)
                except Exception:
                    logger.exception("mark_event_reminded failed (event_id=%s)", ev.id)

    async def _send_one(self, ev) -> bool:
        """
        ev: Event dataclass from your store
        """
        user_id = int(ev.created_by)
        channel_id = int(ev.channel_id)
        remind_in_channel = bool(getattr(ev, "remind_in_channel", 1))

        msg = (
            f"⏰ 活动提醒：**{ev.title}**\n"
            f"开始时间：`{ev.start_iso}`\n"
            f"活动频道：<#{channel_id}>"
        )

        try:
            user = await self.client.fetch_user(user_id)
            await user.send(msg)
            return True
        except discord.Forbidden:
            pass
        except Exception:
            logger.exception("DM send failed (user_id=%s, event_id=%s)", user_id, ev.id)

        if remind_in_channel:
            ch = self.client.get_channel(channel_id)
            if ch is not None:
                try:
                    await ch.send(f"<@{user_id}> {msg}")
                    return True
                except Exception:
                    logger.exception("Channel send failed (channel_id=%s, event_id=%s)", channel_id, ev.id)

        return False
