from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_list(group: app_commands.Group, client) -> None:
    @group.command(name="list", description="List pending reminders in this server")
    @app_commands.describe(limit="Max number of reminders to show (default 10)")
    async def list_reminders(
        interaction: discord.Interaction,
        limit: int = 10,
    ):
        if interaction.guild is None:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return

        limit = max(1, min(int(limit), 20))
        now_iso = _now_utc_iso()

        events = client.store.list_pending_reminders(
            guild_id=interaction.guild.id,
            now_iso=now_iso,
            limit=limit,
        )

        if not events:
            await interaction.response.send_message("No pending reminders.", ephemeral=True)
            return

        lines = []
        for ev in events:
            when = ev.remind_at_iso or "N/A"
            lines.append(f"- 🆔 `{ev.id}` | ⏰ `{when}` | **{ev.title}** | <#{ev.channel_id}>")

        await interaction.response.send_message(
            "Pending reminders:\n" + "\n".join(lines),
            ephemeral=True,
        )
