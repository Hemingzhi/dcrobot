from __future__ import annotations

import discord
from discord import app_commands


def register_cancel(group: app_commands.Group, client) -> None:
    @group.command(name="cancel", description="Cancel an open memo")
    @app_commands.describe(memo_id="Memo ID")
    async def cancel(
        interaction: discord.Interaction,
        memo_id: int,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        rc = client.store.cancel_memo(
            guild_id=interaction.guild.id,
            owner_user_id=interaction.user.id,
            memo_id=int(memo_id),
        )
        if rc <= 0:
            await interaction.response.send_message("Memo not found or not open.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Canceled memo `#{memo_id}`", ephemeral=True)
