from __future__ import annotations

from datetime import datetime, timezone
import discord
from discord import app_commands

MEDIA_TYPES = ["music", "movie", "tv", "anime", "other"]


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def register_add(group: app_commands.Group, client) -> None:
    async def media_type_autocomplete(interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=t, value=t) for t in MEDIA_TYPES if cur in t][:25]

    @group.command(name="add", description="Add a multimedia item to catalog (unique by type+title)")
    @app_commands.describe(media_type="music/movie/tv/anime/other", title="Title/name")
    @app_commands.autocomplete(media_type=media_type_autocomplete)
    async def add(interaction: discord.Interaction, media_type: str, title: str):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        media_type = (media_type or "").strip().lower()
        title = (title or "").strip()
        if not media_type or not title:
            await interaction.response.send_message("media_type and title cannot be empty.", ephemeral=True)
            return
        if media_type not in MEDIA_TYPES:
            await interaction.response.send_message(f"Unknown media_type: `{media_type}`.", ephemeral=True)
            return

        existing = client.store.get_multimedia_item_by_key(
            guild_id=interaction.guild.id,
            media_type=media_type,
            title=title,
        )
        if existing is not None:
            embed = discord.Embed(
                title="⚠️ Already exists",
                description=f"`#{existing.id}` **[{existing.media_type}]** {existing.title}",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        item, _created = client.store.create_or_get_multimedia_item(
            guild_id=interaction.guild.id,
            provider_user_id=interaction.user.id,
            media_type=media_type,
            title=title,
            created_at=_utc_iso_now(),
        )

        embed = discord.Embed(
            title="✅ Added",
            description=f"`#{item.id}` **[{item.media_type}]** {item.title}",
        )
        embed.add_field(name="Provider", value=f"<@{item.provider_user_id}>", inline=True)
        embed.add_field(name="Created at", value=item.created_at, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
