from __future__ import annotations

import discord
from discord import app_commands


def register_show(group: app_commands.Group, client) -> None:
    @group.command(name="show", description="Show a memo item")
    @app_commands.describe(memo_id="Memo ID")
    async def show(
        interaction: discord.Interaction,
        memo_id: int,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item = client.store.get_memo_item_by_id(
            guild_id=interaction.guild.id,
            owner_user_id=interaction.user.id,
            memo_id=int(memo_id),
        )
        if item is None:
            await interaction.response.send_message("Memo not found.", ephemeral=True)
            return

        parts = [
            f"**Memo `#{item.id}`**",
            f"Type: `{item.item_type}`",
            f"Title: **{item.title}**",
            f"Status: `{item.status}`",
        ]
        if item.note:
            parts.append(f"Note: {item.note}")
        if item.due_at_iso:
            parts.append(f"Due: `{item.due_at_iso}`")
        if item.remind_at_iso:
            parts.append(f"Remind: `{item.remind_at_iso}`")
        if item.done_at_iso:
            parts.append(f"Done at: `{item.done_at_iso}`")
        if item.duration_seconds is not None:
            parts.append(f"Duration: `{item.duration_seconds}` seconds")
        if item.thoughts:
            parts.append(f"Thoughts:\n{item.thoughts}")

        await interaction.response.send_message("\n".join(parts), ephemeral=True)
