from __future__ import annotations

import discord
from discord import app_commands
from datetime import datetime, timezone


def _to_utc_iso(dt_str: str | None) -> str | None:
    if dt_str is None:
        return None
    s = (dt_str or "").strip()
    if not s:
        return None

    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        pass

    try:
        dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.isoformat(timespec="seconds")
    except ValueError:
        pass

    dt = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")


def register_reschedule(group: app_commands.Group, client) -> None:
    @group.command(name="reschedule", description="Update due/remind datetime for an open memo")
    @app_commands.describe(
        memo_id="Memo ID",
        due_at="Optional: YYYY-MM-DD or YYYY-MM-DD HH:MM",
        remind_at="Optional: if omitted and due_at provided, remind_at=due_at",
    )
    async def reschedule(
        interaction: discord.Interaction,
        memo_id: int,
        due_at: str | None = None,
        remind_at: str | None = None,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        try:
            due_iso = _to_utc_iso(due_at)
            remind_iso = _to_utc_iso(remind_at)
        except Exception:
            await interaction.response.send_message("Invalid datetime format.", ephemeral=True)
            return

        rc = client.store.reschedule_memo(
            guild_id=interaction.guild.id,
            owner_user_id=interaction.user.id,
            memo_id=int(memo_id),
            due_at_iso=due_iso,
            remind_at_iso=remind_iso,
        )
        if rc <= 0:
            await interaction.response.send_message("Memo not found or not open.", ephemeral=True)
            return

        await interaction.response.send_message(f"🗓️ Rescheduled memo `#{memo_id}`", ephemeral=True)
