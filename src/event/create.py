from datetime import datetime, timedelta

import discord
from discord import app_commands

from src.channel import create_text_channel
from src.restrictions import only_in_channel_id


def _parse_dt(dt_str: str, tzinfo) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=tzinfo)


def register_create(group: app_commands.Group, client):
    allowed_id = int(client.config["restrictions"]["event_create_channel_id"])

    @group.command(name="create", description="Create a new event")
    @only_in_channel_id(allowed_id)
    @app_commands.describe(
        title="Event title",
        start="Start time (YYYY-MM-DD HH:MM, local time)",
        end="End time (optional)",
        description="Optional description",
        create_channel="Create a dedicated text channel",
        channel_name="New channel name (optional)",
        member_limit="Max participants (optional)",
    )
    async def create(
        interaction: discord.Interaction,
        title: str,
        start: str,
        end: str | None = None,
        description: str | None = None,
        create_channel: bool = False,
        channel_name: str | None = None,
        member_limit: int | None = None,
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "Please use this in a server channel.",
                ephemeral=True,
            )
            return

        title = title.strip()
        if len(title) < 2:
            await interaction.response.send_message("Title too short.", ephemeral=True)
            return

        if member_limit is not None and (member_limit < 1 or member_limit > 500):
            await interaction.response.send_message(
                "member_limit must be between 1 and 500.",
                ephemeral=True,
            )
            return

        try:
            tzinfo = client.now_time().tzinfo
            start_dt = _parse_dt(start.strip(), tzinfo)
            end_dt = _parse_dt(end.strip(), tzinfo) if end else None
        except ValueError:
            await interaction.response.send_message(
                "Invalid time format. Use YYYY-MM-DD HH:MM.",
                ephemeral=True,
            )
            return

        if end_dt and end_dt <= start_dt:
            await interaction.response.send_message(
                "End time must be after start time.",
                ephemeral=True,
            )
            return

        expires_dt = (
            end_dt
            if end_dt
            else start_dt
            + (timedelta(minutes=10) if client.mode == "test" else timedelta(days=7))
        )

        created_channel = None
        if create_channel:
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if member is None:
                await interaction.response.send_message("Cannot resolve member.", ephemeral=True)
                return

            created_channel = await create_text_channel(
                guild=interaction.guild,
                requester=member,
                name=(channel_name.strip() if channel_name else title),
                topic=description,
            )

        ev = client.store.create_event(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,  
            title=title,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat() if end_dt else None,
            description=description,
            created_by=interaction.user.id,
            expires_at=expires_dt.isoformat(),
            channel_name=(created_channel.name if created_channel else None),
            member_limit=member_limit,
        )

        display_channel = created_channel or interaction.channel

        embed = discord.Embed(title=f"✅ Event created: {ev.title}")
        embed.add_field(name="Start", value=start_dt.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(
            name="End",
            value=end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "—",
            inline=True,
        )
        embed.add_field(
            name="Expires",
            value=expires_dt.strftime("%Y-%m-%d %H:%M"),
            inline=False,
        )
        embed.add_field(name="Channel", value=display_channel.mention, inline=False)

        if member_limit is not None:
            embed.add_field(name="Max participants", value=str(member_limit), inline=True)

        if description:
            embed.add_field(name="Description", value=description, inline=False)

        embed.set_footer(text=f"Event ID: {ev.id}")

        channel_url = f"https://discord.com/channels/{interaction.guild.id}/{display_channel.id}"
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Go to channel",
                style=discord.ButtonStyle.link,
                url=channel_url,
            )
        )

        if created_channel:
            await created_channel.send(embed=embed, view=view)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
