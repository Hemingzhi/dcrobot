from __future__ import annotations

import discord
from discord import app_commands


def register_unwatch(group: app_commands.Group, client) -> None:
    @group.command(name="unwatch", description="Remove your watch/review record for an item")
    @app_commands.describe(item_id="Catalog item ID")
    async def unwatch(interaction: discord.Interaction, item_id: int):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item = client.store.get_multimedia_item_by_id(guild_id=interaction.guild.id, item_id=int(item_id))
        if item is None:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        rowcount = client.store.delete_multimedia_view(
            guild_id=interaction.guild.id,
            item_id=item.id,
            viewer_user_id=interaction.user.id,
        )
        if rowcount <= 0:
            await interaction.response.send_message("You have no record for this item.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Removed your record for `#{item.id}`.", ephemeral=True)
