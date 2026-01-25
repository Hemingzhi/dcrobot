from __future__ import annotations

import discord
from discord import app_commands


def register_cancel(group: app_commands.Group, client) -> None:
    @group.command(name="cancel", description="Cancel a reminder for an event")
    @app_commands.describe(event_id="Event ID")
    async def cancel_reminder(interaction: discord.Interaction, event_id: int):
        if interaction.guild is None:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return

        ev = client.store.get_event_by_id(event_id=event_id)
        if ev is None or ev.guild_id != interaction.guild.id:
            await interaction.response.send_message("Event not found in this server.", ephemeral=True)
            return

        if not ev.remind_at_iso:
            await interaction.response.send_message("This event has no reminder set.", ephemeral=True)
            return

        updated = client.store.cancel_event_reminder(event_id=event_id)
        if updated <= 0:
            await interaction.response.send_message("Failed to cancel reminder.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Reminder cancelled for event `{event_id}`.", ephemeral=True)
