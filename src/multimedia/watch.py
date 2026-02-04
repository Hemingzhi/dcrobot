from __future__ import annotations

from datetime import datetime, timezone
import discord
from discord import app_commands


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def register_watch(group: app_commands.Group, client) -> None:
    @group.command(name="watch", description="Mark watched/listened and add review (per user)")
    @app_commands.describe(item_id="Catalog item ID", watched="watched/listened?", review="Optional. Use '-' to clear.")
    async def watch(interaction: discord.Interaction, item_id: int, watched: bool = True, review: str | None = None):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item = client.store.get_multimedia_item_by_id(guild_id=interaction.guild.id, item_id=int(item_id))
        if item is None:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        if review is not None and review.strip() == "-":
            review = None

        watched_at = _utc_iso_now() if watched else None

        client.store.upsert_multimedia_view(
            guild_id=interaction.guild.id,
            item_id=item.id,
            viewer_user_id=interaction.user.id,
            watched=1 if watched else 0,
            watched_at=watched_at,
            review=review,
            created_at=_utc_iso_now(),
        )

        embed = discord.Embed(
            title="✅ Updated your status",
            description=f"`#{item.id}` **[{item.media_type}]** {item.title}",
        )
        embed.add_field(name="Watched", value="yes" if watched else "no", inline=True)
        if watched_at:
            embed.add_field(name="Watched at", value=watched_at, inline=True)
        if review:
            embed.add_field(name="Review", value=review[:900], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
