from __future__ import annotations

import discord
from discord import app_commands


def register_my(group: app_commands.Group, client) -> None:
    @group.command(name="my", description="List your watchlist/history")
    @app_commands.describe(watched="Optional filter", limit="1-50", offset="Pagination offset")
    async def my(interaction: discord.Interaction, watched: bool | None = None, limit: int = 20, offset: int = 0):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))

        pairs = client.store.list_my_multimedia(
            guild_id=interaction.guild.id,
            viewer_user_id=interaction.user.id,
            watched=None if watched is None else (1 if watched else 0),
            limit=limit,
            offset=offset,
        )
        if not pairs:
            await interaction.response.send_message("No records found.", ephemeral=True)
            return

        lines = []
        for item, view in pairs:
            flag = "✅" if view.watched else "⏳"
            rev = f" — 💬 {view.review}" if view.review else ""
            lines.append(f"{flag} `#{item.id}` **[{item.media_type}]** {item.title}{rev}")

        embed = discord.Embed(title="🗂️ My multimedia", description="\n".join(lines[:40]))
        embed.set_footer(text=f"limit={limit}, offset={offset}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
