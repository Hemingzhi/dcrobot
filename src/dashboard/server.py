from __future__ import annotations

import discord
from discord import app_commands


def register_server(group: app_commands.Group, client) -> None:
    @group.command(name="server", description="Show server dashboard (overview)")
    async def server(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        now_iso = client.now_time().isoformat()
        data = client.store.dashboard_server(guild_id=interaction.guild.id, now_iso=now_iso)

        e = data["events"]
        m = data["memo"]
        mm = data["multimedia"]

        embed = discord.Embed(title="🏠 Dashboard — Server")
        embed.add_field(
            name="📅 Events",
            value=(
                f"- total: **{e['total']}**\n"
                f"- active: **{e['active']}**\n"
                f"- reminders pending: **{e['reminders_pending']}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="📝 Memo",
            value=(
                f"- open total: **{m['open']}**\n"
                f"- active users: **{m['active_users']}**\n"
                f"- due/overdue: **{m['due_or_overdue']}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎬 Multimedia",
            value=(
                f"- items: **{mm['items']}**\n"
                f"- views(records): **{mm['views']}**"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
