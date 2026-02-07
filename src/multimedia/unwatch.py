from __future__ import annotations

import discord
from discord import app_commands


def register_unwatch(group: app_commands.Group, client) -> None:
    async def item_id_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        if interaction.guild is None:
            return []

        items = client.store.list_multimedia_items_for_guild(
            guild_id=interaction.guild.id,
            limit=25,
        )

        cur = (current or "").strip().lower()

        def matched(it) -> bool:
            if not cur:
                return True
            return str(it.id).startswith(cur) or cur in (it.title or "").lower()

        out: list[app_commands.Choice[int]] = []
        for it in items:
            if not matched(it):
                continue
            out.append(app_commands.Choice(name=f"{it.id} — {it.title}"[:100], value=int(it.id)))
            if len(out) >= 25:
                break
        return out

    @group.command(name="unwatch", description="Remove your watch/review record for an item")
    @app_commands.describe(item_id="Catalog item ID (autocomplete shows id & title)")
    @app_commands.autocomplete(item_id=item_id_autocomplete)
    async def unwatch(interaction: discord.Interaction, item_id: int):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        item = client.store.get_multimedia_item_by_id(
            guild_id=interaction.guild.id,
            item_id=int(item_id),
        )
        if item is None:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return

        rowcount = client.store.delete_multimedia_view(
            guild_id=interaction.guild.id,
            item_id=item.id,
            viewer_user_id=interaction.user.id,
        )
        if rowcount <= 0:
            await interaction.response.send_message("You have no record for this item.", ephemeral=True)
            return

        await interaction.response.send_message(f"🧹 Removed your record for `#{item.id}`.", ephemeral=True)
