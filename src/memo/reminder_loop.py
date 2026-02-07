from discord.ext import tasks
from datetime import datetime, timezone

def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class MemoReminderLoop:
    def __init__(self, client):
        self.client = client

    def start(self):
        self.loop.start()

    @tasks.loop(seconds=30)
    async def loop(self):
        now_iso = _utc_iso_now()
        due = self.client.store.fetch_due_memo_reminders(now_iso=now_iso, limit=25)

        for m in due:
            try:
                user = await self.client.fetch_user(int(m.owner_user_id))
                if user:
                    await user.send(
                        f"⏰ Memo reminder\n"
                        f"`#{m.id}` **[{m.item_type}]** {m.title}\n"
                        f"remind_at: {m.remind_at_iso}\n"
                        f"用 `/memo show {m.id}` 查看，或 `/memo done {m.id}` 完成。"
                    )
            finally:
                self.client.store.mark_memo_reminded(memo_id=m.id)

    @loop.before_loop
    async def before_loop(self):
        await self.client.wait_until_ready()