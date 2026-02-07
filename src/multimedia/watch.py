from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def register_watch(group: app_commands.Group, client) -> None:
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

    @group.command(name="watch", description="Mark watched/listened and add review (per user)")
    @app_commands.describe(
        item_id="Catalog item ID (autocomplete shows id & title)",
        watched="watched/listened?",
        review="Optional text. If empty, stored as '-'",
    )
    @app_commands.autocomplete(item_id=item_id_autocomplete)
    async def watch(
        interaction: discord.Interaction,
        item_id: int,
        watched: bool = True,
        review: str | None = None,
    ):
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

        watched_at = _utc_iso_now() if watched else None
        
        final_review = "-"
        if watched:
            final_review = (review or "").strip() or "-"

        client.store.upsert_multimedia_view(
            guild_id=interaction.guild.id,
            item_id=item.id,
            viewer_user_id=interaction.user.id,
            watched=1 if watched else 0,
            watched_at=watched_at,
            review=final_review,
            created_at=_utc_iso_now(),
        )

        embed = discord.Embed(
            title="✅ Updated your status",
            description=f"`#{item.id}` **[{item.media_type}]** {item.title}",
        )
        embed.add_field(name="Watched", value="yes" if watched else "no", inline=True)
        if watched_at:
            embed.add_field(name="Watched at", value=watched_at, inline=True)
        if watched and final_review != "-":
            embed.add_field(name="Review", value=final_review[:900], inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
