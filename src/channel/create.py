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
    category_name: str | None = None,
    topic: str | None = None,
) -> discord.TextChannel:
    """
    Create a text channel in the guild.
    Requires the bot to have Manage Channels permission.
    """
    me = guild.me
    if me is None:
        raise RuntimeError("Bot member (guild.me) not available")

    bot_perms = guild.me.guild_permissions
    if not bot_perms.manage_channels:
        raise PermissionError("Bot lacks Manage Channels permission")

    channel_name = _slugify(name)[:100]

    existing = discord.utils.get(guild.text_channels, name=channel_name)
    if existing:
        return existing

    category = None
    if category_name:
        category = discord.utils.get(guild.categories, name=category_name)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True),
    }

    ch = await guild.create_text_channel(
        name=channel_name,
        category=category,
        topic=topic,
        overwrites=overwrites,
        reason=f"Created by bot request from {requester} ({requester.id})",
    )
    return ch
