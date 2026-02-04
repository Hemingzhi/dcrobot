from __future__ import annotations

import discord
from discord import app_commands


def register_stats(group: app_commands.Group, client) -> None:
    @group.command(name="stats", description="Show viewers for an item")
    @app_commands.describe(item_id="Catalog item ID", limit="1-50", offset="Pagination offset")
    async def stats(interaction: discord.Interaction, item_id: int, limit: int = 20, offset: int = 0):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        limit = max(1, min(int(limit), 50))
        offset = max(0, int(offset))

        item = client.store.get_multimedia_item_by_id(guild_id=interaction.guild.id, item_id=int(item_id))
        if item is None:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        views = client.store.list_multimedia_item_views(
            guild_id=interaction.guild.id,
            item_id=item.id,
            limit=limit,
            offset=offset,
        )
        if not views:
            await interaction.response.send_message("No viewers yet.", ephemeral=True)
            return

        lines = []
        for v in views:
            flag = "✅" if v.watched else "⏳"
            who = f"<@{v.viewer_user_id}>"
            when = v.watched_at or v.created_at
            rev = f" — 💬 {v.review}" if v.review else ""
            lines.append(f"{flag} {who} — {when}{rev}")

        embed = discord.Embed(
            title="👥 Item stats",
            description=f"`#{item.id}` **[{item.media_type}]** {item.title}\n\n" + "\n".join(lines[:40]),
        )
        embed.set_footer(text=f"limit={limit}, offset={offset}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
