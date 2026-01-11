from __future__ import annotations

import discord
from discord import app_commands

from src.channel import get_or_create_category
from src.restrictions import only_in_event_create_channel


def register_category_create(group: app_commands.Group, client) -> None:
    @group.command(name="create", description="Create a category option (and Discord category if needed)")
    @only_in_event_create_channel(client)
    @app_commands.describe(name="Category name")
    async def create_cmd(interaction: discord.Interaction, name: str):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        name = (name or "").strip()
        if not name:
            await interaction.response.send_message("Category name cannot be empty.", ephemeral=True)
            return

        if hasattr(client.store, "has_category_option") and client.store.has_category_option(
            guild_id=interaction.guild.id,
            name=name,
        ):
            await interaction.response.send_message(f"ℹ️ Category already exists: **{name}**", ephemeral=True)
            return

        try:
            await get_or_create_category(guild=interaction.guild, name=name)
        except PermissionError:
            await interaction.response.send_message(
                "I don't have permission to create categories. Please grant me **Manage Channels**.",
                ephemeral=True,
            )
            return
        except Exception as e:
            await interaction.response.send_message(f"Failed to create/find category: {e}", ephemeral=True)
            return

        client.store.add_category_option(guild_id=interaction.guild.id, name=name)
        await interaction.response.send_message(f"✅ Category created: **{name}**", ephemeral=True)
