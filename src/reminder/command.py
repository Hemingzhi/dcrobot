
from datetime import datetime, timezone
import zoneinfo

import discord
from discord import app_commands

PARIS = zoneinfo.ZoneInfo("Europe/Paris")


def _parse_paris_to_utc_iso(dt_str: str) -> str:
    local = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=PARIS)
    return local.astimezone(timezone.utc).isoformat()


def register_reminder_commands(tree: app_commands.CommandTree, client):
    group = app_commands.Group(
        name="reminder",
        description="Reminder management",
    )

    @group.command(name="set", description="Set a reminder for an event")
    @app_commands.describe(
        event_id="Event ID",
        when="YYYY-MM-DD HH:MM (Europe/Paris)",
        in_channel="Ping in event channel if DM fails",
    )
    async def set_reminder(
        interaction: discord.Interaction,
        event_id: int,
        when: str,
        in_channel: bool = True,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Please use this in a server.",
                ephemeral=True,
            )
            return

        try:
            remind_at_iso = _parse_paris_to_utc_iso(when)
        except ValueError:
            await interaction.response.send_message(
                "Invalid datetime format. Use YYYY-MM-DD HH:MM",
                ephemeral=True,
            )
            return

        updated = client.store.set_event_reminder(
            event_id=event_id,
            remind_at_iso=remind_at_iso,
            remind_in_channel=in_channel,
        )

        if updated <= 0:
            await interaction.response.send_message(
                "Event not found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"⏰ Reminder set for event `{event_id}` at **{when}** (Paris)",
            ephemeral=True,
        )

    tree.add_command(group)
