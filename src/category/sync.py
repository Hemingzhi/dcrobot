import discord
from discord import app_commands

from src.restrictions import only_in_event_create_channel

def register_category_sync(group: app_commands.Group, client) -> None:
    @group.command(name="sync", description="Import all Discord categories into DB options")
    @only_in_event_create_channel(client)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def sync_cmd(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        count = 0
        for c in interaction.guild.categories:
            client.store.add_category_option(guild_id=interaction.guild.id, name=c.name)
            count += 1

        await interaction.response.send_message(f"✅ Synced {count} Discord categories into DB options.", ephemeral=True)
