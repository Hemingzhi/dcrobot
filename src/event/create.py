from datetime import datetime, timedelta
from discord import app_commands
import discord


def _parse_dt(dt_str: str, tzinfo) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=tzinfo)


def register_create(group: app_commands.Group, client):
    @group.command(name="create", description="Create a new event")
    @app_commands.describe(
        title="Event title",
        start="Start time, format: YYYY-MM-DD HH:MM (UTC+2)",
        end="End time, format: YYYY-MM-DD HH:MM (optional)",
        description="Optional description",
    )
    async def create(
        interaction: discord.Interaction,
        title: str,
        start: str,
        end: str | None = None,
        description: str | None = None,
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        title = title.strip()
        if len(title) < 2:
            await interaction.response.send_message("Title too short.", ephemeral=True)
            return

        try:
            start_dt = _parse_dt(start.strip(), client.now_time().tzinfo)
            end_dt = _parse_dt(end.strip(), client.now_time().tzinfo) if end else None
        except ValueError:
            await interaction.response.send_message(
                "Time format error. Use `YYYY-MM-DD HH:MM` e.g. `2026-01-08 19:30` (UTC+2).",
                ephemeral=True,
            )
            return

        if end_dt and end_dt <= start_dt:
            await interaction.response.send_message("End must be after start.", ephemeral=True)
            return

        if end_dt:
            expires_dt = end_dt
        else:
            expires_dt = start_dt + (timedelta(minutes=10) if client.mode == "test" else timedelta(days=7))

        ev = client.store.create_event(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            title=title,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat() if end_dt else None,
            description=(description.strip() if description else None),
            created_by=interaction.user.id,
            expires_at=expires_dt.isoformat(),
        )

        embed = discord.Embed(title=f"✅ Event created: {ev.title}")
        embed.add_field(name="Start (UTC+2)", value=start_dt.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="End (UTC+2)", value=(end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "—"), inline=True)
        embed.add_field(name="Expires (UTC+2)", value=expires_dt.strftime("%Y-%m-%d %H:%M"), inline=False)

        if ev.description:
            embed.add_field(name="Description", value=ev.description, inline=False)

        embed.set_footer(text=f"Event ID: {ev.id} | Created by {interaction.user}")
        await interaction.response.send_message(embed=embed)
