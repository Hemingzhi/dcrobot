from __future__ import annotations

import discord
from discord import app_commands


def register_done(group: app_commands.Group, client) -> None:
    @group.command(name="done", description="Mark memo as done")
    @app_commands.describe(
        memo_id="Memo ID",
        duration_seconds="Optional: how long you spent (seconds)",
        thoughts="Optional: post-thoughts (max 9999 chars, may be limited by Discord UI)",
    )
    async def done(
        interaction: discord.Interaction,
        memo_id: int,
        duration_seconds: int | None = None,
        thoughts: str | None = None,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        if duration_seconds is not None and duration_seconds < 0:
            await interaction.response.send_message("duration_seconds must be >= 0.", ephemeral=True)
            return

        try:
            rc = client.store.mark_memo_done(
                guild_id=interaction.guild.id,
                owner_user_id=interaction.user.id,
                memo_id=int(memo_id),
                duration_seconds=duration_seconds,
                thoughts=thoughts,
            )
        except Exception as e:
            await interaction.response.send_message(f"Failed: {e}", ephemeral=True)
            return

        if rc <= 0:
            await interaction.response.send_message("Memo not found or not open.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Done memo `#{memo_id}`", ephemeral=True)
