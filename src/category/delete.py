from __future__ import annotations

import discord
from discord import app_commands

from src.restrictions import only_in_event_create_channel


def register_category_delete(group: app_commands.Group, client) -> None:
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        if interaction.guild is None:
            return []
        if not hasattr(client.store, "list_all_category_options"):
            return []

        names = client.store.list_all_category_options(guild_id=interaction.guild.id, limit=200)
        cur = (current or "").lower()
        matched = [n for n in names if cur in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in matched]

    @group.command(name="delete", description="Delete a category option from DB")
    @only_in_event_create_channel(client)
    @app_commands.autocomplete(name=category_autocomplete)
    @app_commands.describe(name="Category name (must exist)")
    async def delete_cmd(interaction: discord.Interaction, name: str):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        name = (name or "").strip()
        if not name:
            await interaction.response.send_message("Category name cannot be empty.", ephemeral=True)
            return

        if not hasattr(client.store, "delete_category_option"):
            await interaction.response.send_message("Store method `delete_category_option` is missing.", ephemeral=True)
            return

        deleted = client.store.delete_category_option(guild_id=interaction.guild.id, name=name)
        if deleted:
            await interaction.response.send_message(f"🗑️ Deleted category option: **{name}**", ephemeral=True)
        else:
            await interaction.response.send_message(f"Category not found: **{name}**", ephemeral=True)
