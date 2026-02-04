from __future__ import annotations

import discord
from discord import app_commands


def _can_delete_item(interaction: discord.Interaction, provider_user_id: int) -> bool:
    if interaction.user is None:
        return False
    if interaction.user.id == provider_user_id:
        return True
    perms = interaction.user.guild_permissions
    return bool(perms.administrator or perms.manage_guild)


def register_delete_item(group: app_commands.Group, client) -> None:
    @group.command(name="delete-item", description="Delete a catalog item (provider or admin only)")
    @app_commands.describe(item_id="Catalog item ID")
    async def delete_item(interaction: discord.Interaction, item_id: int):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item = client.store.get_multimedia_item_by_id(guild_id=interaction.guild.id, item_id=int(item_id))
        if item is None:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        if not _can_delete_item(interaction, item.provider_user_id):
            await interaction.response.send_message("Permission denied.", ephemeral=True)
            return

        deleted_views, deleted_items = client.store.delete_multimedia_item(
            guild_id=interaction.guild.id,
            item_id=item.id,
        )
        if deleted_items <= 0:
            await interaction.response.send_message("Nothing deleted.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🗑️ Deleted item `#{item.id}` (views removed: {deleted_views}).",
            ephemeral=True,
        )
