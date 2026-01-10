import discord

def only_in_channel_id(channel_id: int):
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel is None:
            await interaction.response.send_message(
                "Please use this command in a server channel.",
                ephemeral=True,
            )
            return False

        if interaction.channel.id != channel_id:
            await interaction.response.send_message(
                "This command can only be used in the designated channel.",
                ephemeral=True,
            )
            return False

        return True

    return discord.app_commands.check(predicate)
