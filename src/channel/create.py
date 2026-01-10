import re
import discord


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "event"


async def create_text_channel(
    *,
    guild: discord.Guild,
    requester: discord.Member,
    name: str,
    category: discord.CategoryChannel | None = None,
    topic: str | None = None,
) -> discord.TextChannel:
    me = guild.me
    if me is None:
        raise RuntimeError("Bot member not available")

    if not me.guild_permissions.manage_channels:
        raise PermissionError("Bot lacks Manage Channels permission")

    channel_name = _slugify(name)[:100]

    existing = discord.utils.get(guild.text_channels, name=channel_name)
    if existing:
        return existing

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        topic=topic,
        reason=f"Created by bot request from {requester}",
    )
    return channel
