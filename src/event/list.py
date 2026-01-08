from discord import app_commands
import discord


def register_list(group: app_commands.Group, client):
    @group.command(name="list", description="List active events in this channel")
    @app_commands.describe(limit="Max number of events to show (default 10, max 20)")
    async def list_events(interaction: discord.Interaction, limit: int = 10):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        limit = max(1, min(20, limit))
        now_iso = client.now_time().isoformat()

        events = client.store.list_active_events(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            now_iso=now_iso,
            limit=limit,
        )

        if not events:
            await interaction.response.send_message("No active events in this channel.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📅 Active events ({len(events)})")

        lines = []
        for ev in events:
            start_s = ev.start_iso[:16].replace("T", " ")
            end_s = ev.end_iso[:16].replace("T", " ") if ev.end_iso else "—"
            exp_s = ev.expires_at[:16].replace("T", " ")

            lines.append(f"**#{ev.id}** · {ev.title}\nStart: `{start_s}` · End: `{end_s}` · Expires: `{exp_s}`")

        text = "\n\n".join(lines)
        if len(text) > 3500:
            text = text[:3500] + "\n\n…(truncated)"

        embed.description = text
        await interaction.response.send_message(embed=embed, ephemeral=True)
