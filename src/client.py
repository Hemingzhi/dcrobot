import asyncio
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands

from src.event_storage import EventStore


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, mode: str, project_root: Path, time_now_func):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

        self.mode = mode
        self.now_time = time_now_func

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
        while True:
            try:
                deleted = self.store.delete_expired(self.now_time().isoformat())
                if deleted:
                    print(f"[cleanup] deleted {deleted} expired events at {self.now_time().isoformat()}")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[cleanup] error: {e}")
                await asyncio.sleep(interval)
