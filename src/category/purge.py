from __future__ import annotations

import discord
from discord import app_commands

from src.restrictions import only_in_event_create_channel


def _is_allowed_purge(interaction: discord.Interaction, client) -> bool:
    cfg = (getattr(client, "config", {}) or {}).get("category", {}).get("purge", {})
    allowed_role_ids = set(cfg.get("allowed_role_ids") or [])
    allowed_user_ids = set(cfg.get("allowed_user_ids") or [])

    if interaction.user is None:
        return False

    if int(interaction.user.id) in allowed_user_ids:
        return True

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member is None:
        return False

    if interaction.guild and interaction.guild.owner_id == member.id:
        return True

    if allowed_role_ids:
        member_role_ids = {r.id for r in member.roles}
        if member_role_ids & allowed_role_ids:
            return True

    return False


def register_category_purge(group: app_commands.Group, client) -> None:
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        if interaction.guild is None:
            return []
        if not hasattr(client.store, "list_all_category_options"):
            return []
        names = client.store.list_all_category_options(guild_id=interaction.guild.id, limit=200)
        cur = (current or "").lower()
        matched = [n for n in names if cur in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in matched]

    @group.command(
        name="purge",
        description="DANGEROUS: delete the Discord category (optionally with all its channels) and remove DB option",
    )
    @only_in_event_create_channel(client)
    @app_commands.checks.has_permissions(manage_channels=True) 
    @app_commands.autocomplete(name=category_autocomplete)
    @app_commands.describe(
        name="Category name (must exist in DB and Discord)",
        force="If true, delete ALL channels under this category before deleting it (DANGEROUS)",
    )
    async def purge_cmd(interaction: discord.Interaction, name: str, force: bool = False):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        if not _is_allowed_purge(interaction, client):
            await interaction.response.send_message(
                "⛔ You are not allowed to use `/category purge`.",
                ephemeral=True,
            )
            return

        name = (name or "").strip()
        if not name:
            await interaction.response.send_message("Category name cannot be empty.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if hasattr(client.store, "has_category_option"):
            if not client.store.has_category_option(guild_id=interaction.guild.id, name=name):
                await interaction.followup.send(f"Category option not found in DB: **{name}**", ephemeral=True)
                return

        cat = discord.utils.get(interaction.guild.categories, name=name)
        if cat is None:
            await interaction.followup.send(
                f"Discord category **{name}** not found. (DB option may still exist.)",
                ephemeral=True,
            )
            return

        children = list(cat.channels)  
        if children and not force:
            await interaction.followup.send(
                f"⚠️ Category **{name}** is not empty ({len(children)} channels).\n"
                f"Refusing to purge.\n"
                f"If you really want to delete EVERYTHING under it, rerun with `force=true`.",
                ephemeral=True,
            )
            return

        if children and force:
            failed = []
            for ch in children:
                try:
                    await ch.delete(reason=f"Purged by {interaction.user} via /category purge force=true")
                except Exception:
                    failed.append(ch.name)

            if failed:
                await interaction.followup.send(
                    "⚠️ Deleted some channels but failed on:\n"
                    + "\n".join([f"- {n}" for n in failed])
                    + "\nAbort deleting the category itself to avoid half-broken state.",
                    ephemeral=True,
                )
                return

        try:
            await cat.delete(reason=f"Purged by {interaction.user} via /category purge")
        except Exception as e:
            await interaction.followup.send(f"Failed to delete Discord category: {e}", ephemeral=True)
            return

        deleted_db = 0
        if hasattr(client.store, "delete_category_option"):
            deleted_db = client.store.delete_category_option(guild_id=interaction.guild.id, name=name)

        await interaction.followup.send(
            f"🔥 Purged category **{name}**.\n"
            f"- Discord category deleted: ✅\n"
            f"- DB option deleted: {'✅' if deleted_db else '⚠️ (not found / method missing)'}",
            ephemeral=True,
        )
