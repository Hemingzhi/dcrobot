import discord

def only_in_event_create_channel(client):

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "Please use this command in a server channel.",
                ephemeral=True,
            )
            return False

        cfg = client.config.get("event", {})
        allowed_name = cfg.get("event_create_channel_name")

        if not allowed_name:
            await interaction.response.send_message(
                "Event create channel is not configured.",
                ephemeral=True,
            )
            return False

        if interaction.channel.name != allowed_name:
            target = discord.utils.get(
                interaction.guild.text_channels,
                name=allowed_name,
            )

            hint = (
                f"Please use this command in {target.mention}."
                if target
                else f"Please use this command in **#{allowed_name}**."
            )

            await interaction.response.send_message(hint, ephemeral=True)
            return False

        return True

    return discord.app_commands.check(predicate)
