from __future__ import annotations

import discord
from discord import app_commands


def _fmt_avg_seconds(x: float | None) -> str:
    if x is None:
        return "—"
    sec = int(round(x))
    if sec < 60:
        return f"{sec}s"
    mins = sec // 60
    if mins < 60:
        return f"{mins}m"
    h = mins // 60
    m = mins % 60
    return f"{h}h {m}m"


def register_me(group: app_commands.Group, client) -> None:
    @group.command(name="me", description="Show my dashboard (events/memo/multimedia)")
    async def me(interaction: discord.Interaction):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        now_iso = client.now_time().isoformat()
        data = client.store.dashboard_me(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            now_iso=now_iso,
        )

        e = data["events"]
        m = data["memo"]
        mm = data["multimedia"]

        embed = discord.Embed(title="📊 Dashboard — Me")
        embed.add_field(
            name="📅 Events",
            value=(
                f"- created: **{e['total_created']}**\n"
                f"- active/future: **{e['active_future']}**\n"
                f"- reminders pending: **{e['reminders_pending']}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="📝 Memo",
            value=(
                f"- open: **{m['open']}** (overdue: **{m['overdue']}**)\n"
                f"- done: **{m['done']}**\n"
                f"- canceled: **{m['canceled']}**\n"
                f"- avg duration: **{_fmt_avg_seconds(m['avg_duration_seconds'])}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎬 Multimedia",
            value=(
                f"- records: **{mm['records']}**\n"
                f"- watched: **{mm['watched']}** / unwatched: **{mm['unwatched']}**\n"
                f"- reviews: **{mm['reviews']}**"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
