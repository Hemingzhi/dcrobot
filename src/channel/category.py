import discord


async def get_or_create_category(
    *,
    guild: discord.Guild,
    name: str,
) -> discord.CategoryChannel:
    """
    Get category by name; if not exists, create it.

    Requires Manage Channels permission to create.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Category name cannot be empty")

    existing = discord.utils.get(guild.categories, name=name)
    if existing:
        return existing

    me = guild.me
    if me is None:
        raise RuntimeError("Bot member not available")

    if not me.guild_permissions.manage_channels:
        raise PermissionError("Bot lacks Manage Channels permission")

    cat = await guild.create_category(name=name, reason="Created by bot for event channels")
    return cat
