from __future__ import annotations

import discord
from discord import app_commands
from datetime import datetime, timezone


def _to_utc_iso(dt_str: str | None) -> str | None:
    """
    Accept:
      - YYYY-MM-DD
      - YYYY-MM-DD HH:MM
      - ISO8601 (pass-through if parseable)
    Convert to UTC ISO string.
    """
    if not dt_str:
        return None

    s = (dt_str or "").strip()
    if not s:
        return None

    # Try ISO first
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        pass

    # YYYY-MM-DD
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.isoformat(timespec="seconds")
    except ValueError:
        pass

    # YYYY-MM-DD HH:MM
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")


def register_add(group: app_commands.Group, client) -> None:
    @group.command(name="add", description="Create a personal memo/todo item")
    @app_commands.describe(
        item_type="Type: task/movie/anime/book/game/...",
        title="Title",
        due_at="Optional: YYYY-MM-DD or YYYY-MM-DD HH:MM (treated as UTC in this simple parser)",
        remind_at="Optional: if omitted and due_at provided, remind_at=due_at",
        note="Optional note",
    )
    async def add(
        interaction: discord.Interaction,
        item_type: str,
        title: str,
        due_at: str | None = None,
        remind_at: str | None = None,
        note: str | None = None,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item_type = (item_type or "").strip().lower()
        title = (title or "").strip()
        note = (note or None)

        if not item_type or not title:
            await interaction.response.send_message("item_type/title cannot be empty.", ephemeral=True)
            return

        try:
            due_iso = _to_utc_iso(due_at)
            remind_iso = _to_utc_iso(remind_at)
        except Exception:
            await interaction.response.send_message("Invalid datetime format.", ephemeral=True)
            return

        try:
            item = client.store.create_memo_item(
                guild_id=interaction.guild.id,
                owner_user_id=interaction.user.id,
                item_type=item_type,
                title=title,
                note=note,
                due_at_iso=due_iso,
                remind_at_iso=remind_iso,
            )
        except Exception as e:
            await interaction.response.send_message(f"Failed: {e}", ephemeral=True)
            return

        msg = f"📝 Created memo `#{item.id}` **[{item.item_type}]** {item.title}"
        if item.due_at_iso:
            msg += f"\nDue: `{item.due_at_iso}`"
        if item.remind_at_iso:
            msg += f"\nRemind: `{item.remind_at_iso}`"
        await interaction.response.send_message(msg, ephemeral=True)
