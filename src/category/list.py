from __future__ import annotations

import discord
from discord import app_commands

from src.restrictions import only_in_event_create_channel


def register_category_list(group: app_commands.Group, client) -> None:
    @group.command(name="list", description="List existing category options")
    @only_in_event_create_channel(client)
    async def list_cmd(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        if not hasattr(client.store, "list_all_category_options"):
            await interaction.response.send_message("Store method `list_all_category_options` is missing.", ephemeral=True)
            return

        names = client.store.list_all_category_options(guild_id=interaction.guild.id, limit=200)
        if not names:
            await interaction.response.send_message(
                "No categories yet. Create one with `/category create`.",
                ephemeral=True,
            )
            return

        shown = names[:50]
        tail = "" if len(names) <= 50 else f"\n…还有 {len(names)-50} 个未显示"
        msg = "📚 Categories:\n" + "\n".join([f"- {n}" for n in shown]) + tail
        await interaction.response.send_message(msg, ephemeral=True)
