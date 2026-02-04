from __future__ import annotations

import discord
from discord import app_commands

MEDIA_TYPES = ["music", "movie", "tv", "anime", "other"]


def register_update(group: app_commands.Group, client) -> None:
    async def media_type_autocomplete(interaction: discord.Interaction, current: str):
        cur = (current or "").lower()
        return [app_commands.Choice(name=t, value=t) for t in MEDIA_TYPES if cur in t][:25]

    @group.command(name="update", description="Update a multimedia item by ID")
    @app_commands.describe(
        item_id="Item ID",
        media_type="Optional new type",
        title="Optional new title",
        watched="Optional watched status",
        review="Optional review. Use '-' to clear.",
    )
    @app_commands.autocomplete(media_type=media_type_autocomplete)
    async def update(
        interaction: discord.Interaction,
        item_id: int,
        media_type: str | None = None,
        title: str | None = None,
        watched: bool | None = None,
        review: str | None = None,
    ):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        if media_type is not None:
            media_type = media_type.strip().lower()
            if media_type not in MEDIA_TYPES:
                await interaction.response.send_message(f"Unknown media_type: `{media_type}`.", ephemeral=True)
                return

        if title is not None:
            title = title.strip()
            if not title:
                await interaction.response.send_message("title cannot be empty.", ephemeral=True)
                return

        if review is not None and review.strip() == "-":
            review = None  # 清成 NULL

        rowcount = client.store.update_multimedia_item(
            guild_id=interaction.guild.id,
            item_id=int(item_id),
            media_type=media_type,
            title=title,
            watched=(None if watched is None else (1 if watched else 0)),
            review=review,
        )

        if rowcount <= 0:
            await interaction.response.send_message("Nothing updated (wrong ID or no fields).", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Updated item `#{item_id}`.")
