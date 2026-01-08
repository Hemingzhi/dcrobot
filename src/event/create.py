from datetime import datetime, timedelta
from discord import app_commands
import discord

from src.channel import create_text_channel


def _parse_dt(dt_str: str, tzinfo) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=tzinfo)


def register_create(group: app_commands.Group, client):
    @group.command(name="create", description="Create a new event")
    @app_commands.describe(
        title="Event title",
        start="Start time, format: YYYY-MM-DD HH:MM (UTC+2)",
        end="End time, format: YYYY-MM-DD HH:MM (optional)",
        description="Optional description",
        create_channel="Create a new text channel for this event",
        channel_name="New channel name (optional). If empty, it uses the title",
    )
    async def create(
        interaction: discord.Interaction,
        title: str,
        start: str,
        end: str | None = None,
        description: str | None = None,
        create_channel: bool = False,
        channel_name: str | None = None,
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        title = title.strip()
        if len(title) < 2:
            await interaction.response.send_message("Title too short.", ephemeral=True)
            return

        try:
            tzinfo = client.now_time().tzinfo
            start_dt = _parse_dt(start.strip(), tzinfo)
            end_dt = _parse_dt(end.strip(), tzinfo) if end else None
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

        target_channel = interaction.channel
        created_channel = None

        if create_channel:
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if member is None:
                await interaction.response.send_message("Cannot resolve member in this guild.", ephemeral=True)
                return

            try:
                created_channel = await create_text_channel(
                    guild=interaction.guild,
                    requester=member,
                    name=(channel_name.strip() if channel_name else title),
                    category_name=None, 
                    topic=f"Event: {title}",
                )
                target_channel = created_channel
            except PermissionError:
                await interaction.response.send_message(
                    "I don't have permission to create channels. Please grant me **Manage Channels**.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                await interaction.response.send_message(f"Failed to create channel: {e}", ephemeral=True)
                return

        ev = client.store.create_event(
            guild_id=interaction.guild.id,
            channel_id=target_channel.id,
            title=title,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat() if end_dt else None,
            description=(description.strip() if description else None),
            created_by=interaction.user.id,
            expires_at=expires_dt.isoformat(),
            channel_name=created_channel.name,
        )

        embed = discord.Embed(title=f"✅ Event created: {ev.title}")
        embed.add_field(name="Start (UTC+2)", value=start_dt.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="End (UTC+2)", value=(end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "—"), inline=True)
        embed.add_field(name="Expires (UTC+2)", value=expires_dt.strftime("%Y-%m-%d %H:%M"), inline=False)
        embed.add_field(name="Channel", value=target_channel.mention, inline=False)

        if ev.description:
            embed.add_field(name="Description", value=ev.description, inline=False)

        embed.set_footer(text=f"Event ID: {ev.id} | Created by {interaction.user}")

        if created_channel:
            await created_channel.send(embed=embed)

        await interaction.response.send_message(embed=embed, ephemeral=True)
