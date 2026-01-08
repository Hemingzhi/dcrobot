import discord

def only_in_channel_id(channel_id: int, *, hint: str | None = None):
    """
    Decorator for app_commands slash commands.

    If invoked outside the allowed channel_id, reply ephemeral and stop.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel is None or interaction.guild is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return False

        if interaction.channel.id != int(channel_id):
            ch = interaction.guild.get_channel(int(channel_id))
            msg = hint or (f"Please use this command in {ch.mention}." if ch else "This command is restricted to a specific channel.")
            await interaction.response.send_message(msg, ephemeral=True)
            return False

        return True

    return discord.app_commands.check(predicate)
