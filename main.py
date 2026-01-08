import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands

from src.config_loading import load_config
from src.event_storage import EventStore

TIME_TZ = timezone(timedelta(hours=2))

def now_time() -> datetime:
    return datetime.now(tz=TIME_TZ)

def _parse_dt(dt_str: str) -> datetime:
    """
    Format: YYYY-MM-DD HH:MM
    Example: 2026-01-08 19:30
    """
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=TIME_TZ)

config = load_config()
TOKEN = config["discord"]["token"]
MODE = (config.get("app", {}).get("mode") or "test").lower()  # "test" or "prod"

intents = discord.Intents.default()
intents.members = True         
intents.message_content = True


class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

        project_root = Path(__file__).resolve().parent

        self.store = EventStore(project_root / "events.db")
        self._cleanup_task: asyncio.Task | None = None

    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"[sync] synced {len(synced)} commands: {[c.name for c in synced]}")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def close(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        await super().close()

    async def _cleanup_loop(self):
        interval = 10 if MODE == "test" else 60

        while True:
            try:
                deleted = self.store.delete_expired(now_time().isoformat())
                if deleted:
                    print(f"[cleanup] deleted {deleted} expired events")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[cleanup] error: {e}")
                await asyncio.sleep(interval)

client = MyClient()

@client.tree.command(name="event_create", description="Create a new event (time in UTC+2)")
@app_commands.describe(
    title="Event title",
    start="Start time, format: YYYY-MM-DD HH:MM (UTC+2)",
    end="End time, format: YYYY-MM-DD HH:MM (optional)",
    description="Optional description",
)
async def event_create(
    interaction: discord.Interaction,
    title: str,
    start: str,
    end: str | None = None,
    description: str | None = None,
):
    if interaction.guild is None or interaction.channel is None:
        await interaction.response.send_message(
            "Please use this in a server channel.", ephemeral=True
        )
        return

    title = title.strip()
    if len(title) < 2:
        await interaction.response.send_message("Title too short.", ephemeral=True)
        return

    try:
        start_dt = _parse_dt(start.strip())
        end_dt = _parse_dt(end.strip()) if end else None
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
        expires_dt = start_dt + (timedelta(minutes=10) if MODE == "test" else timedelta(days=7))

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
    embed.add_field(
        name="End (UTC+2)",
        value=(end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "—"),
        inline=True,
    )
    embed.add_field(
        name="Expires (UTC+2)",
        value=expires_dt.strftime("%Y-%m-%d %H:%M"),
        inline=False,
    )
    if ev.description:
        embed.add_field(name="Description", value=ev.description, inline=False)

    embed.set_footer(text=f"Event ID: {ev.id} | Created by {interaction.user}")
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="event_list", description="List active events in this channel")
@app_commands.describe(limit="Max number of events to show (default 10, max 20)")
async def event_list(interaction: discord.Interaction, limit: int = 10):
    if interaction.guild is None or interaction.channel is None:
        await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
        return

    limit = max(1, min(20, limit))
    now_iso = now_time().isoformat()

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

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (id: {client.user.id}) | MODE={MODE}")

@client.event
async def on_member_join(member: discord.Member):
    cfg = load_config()
    welcome_cfg = cfg.get("welcome", {})

    channel = None

    if "channel_name" in welcome_cfg:
        channel = discord.utils.get(
            member.guild.text_channels,
            name=welcome_cfg["channel_name"],
        )

    if channel is None:
        print("[welcome] welcome channel not found")
        return

    perms = channel.permissions_for(member.guild.me)
    if not perms.send_messages:
        print("[welcome] no permission to send messages")
        return

    await channel.send(
        f"欢迎 {member.mention} 加入 🎉\n"
        f"输入 `/event_create` 可以创建活动。"
    )


client.run(TOKEN)

