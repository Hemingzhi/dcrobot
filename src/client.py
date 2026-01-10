import asyncio
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands

from src.channel import delete_text_channel_by_name
from src.event_storage import EventStore


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, mode: str, project_root: Path, time_now_func, config: dict):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

        self.mode = mode
        self.now_time = time_now_func
        self.config = config 

        self.store = EventStore(project_root / "events.db")
        self._cleanup_task: asyncio.Task | None = None

    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"[sync] synced {len(synced)} commands: {[c.name for c in synced]}")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def close(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await super().close()

    async def _cleanup_loop(self):
        interval = 10 if self.mode == "test" else 60

        protected_names = set()
        welcome_name = self.config.get("welcome", {}).get("channel_name")
        if welcome_name:
            protected_names.add(welcome_name)

        while True:
            try:
                now_iso = self.now_time().isoformat()
                expired = self.store.fetch_expired_events(now_iso)

                for ev in expired:
                    if not ev.channel_name:
                        continue
                    if ev.channel_name in protected_names:
                        print(f"[cleanup] skip protected channel #{ev.channel_name}")
                        continue

                    guild = self.get_guild(int(ev.guild_id))
                    if guild is None:
                        continue

                    try:
                        deleted = await delete_text_channel_by_name(
                            guild=guild,
                            channel_name=ev.channel_name,
                            reason=f"Event expired (id={ev.id})",
                        )
                        if deleted:
                            print(f"[cleanup] deleted channel #{ev.channel_name} for event {ev.id}")
                    except Exception as e:
                        print(f"[cleanup] failed to delete channel #{ev.channel_name} for event {ev.id}: {e}")

                deleted_rows = self.store.delete_expired(now_iso)
                if deleted_rows:
                    print(f"[cleanup] deleted {deleted_rows} expired events from db")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[cleanup] error: {e}")
                await asyncio.sleep(interval)
