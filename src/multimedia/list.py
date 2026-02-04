from __future__ import annotations

import discord
from discord import app_commands

MEDIA_TYPES = ["music", "movie", "tv", "anime", "other"]


def register_list(group: app_commands.Group, client) -> None:
    async def media_type_autocomplete(interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=t, value=t) for t in MEDIA_TYPES if cur in t][:25]

    @group.command(name="list", description="List catalog items")
    @app_commands.describe(media_type="Optional filter", limit="1-50", offset="Pagination offset")
    @app_commands.autocomplete(media_type=media_type_autocomplete)
    async def list_cmd(interaction: discord.Interaction, media_type: str | None = None, limit: int = 20, offset: int = 0):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))

        items = client.store.list_multimedia_items(
            guild_id=interaction.guild.id,
            media_type=media_type,
            limit=limit,
            offset=offset,
        )

        if not items:
            await interaction.response.send_message("No items found.", ephemeral=True)
            return

        lines = [f"`#{it.id}` **[{it.media_type}]** {it.title} — by <@{it.provider_user_id}>" for it in items]
        embed = discord.Embed(title="📚 Multimedia catalog", description="\n".join(lines[:40]))
        embed.set_footer(text=f"limit={limit}, offset={offset}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
