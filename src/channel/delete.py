import discord

async def delete_channel_by_name(
    *,
    guild: discord.Guild,
    channel_name: str,
    reason: str,
) -> bool:
    if not channel_name:
        return False

    channel_name = channel_name.strip()
    if not channel_name:
        return False

    channel = (
        discord.utils.get(guild.text_channels, name=channel_name)
        or discord.utils.get(guild.voice_channels, name=channel_name)
    )

    if channel is None:
        return False

    me = guild.me
    if me is None:
        raise RuntimeError("Bot member (guild.me) not available")

    if not channel.permissions_for(me).manage_channels:
        raise PermissionError("Bot lacks permission to delete this channel")

    await channel.delete(reason=reason)
    return True
