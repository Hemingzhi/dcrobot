import discord


def register_base_events(client, config: dict):
    welcome_cfg = config.get("welcome", {})
    welcome_channel_name = welcome_cfg.get("channel_name")

    @client.event
    async def on_member_join(member: discord.Member):
        if not welcome_channel_name:
            print("[welcome] welcome.channel_name not configured")
            return

        channel = discord.utils.get(member.guild.text_channels, name=welcome_channel_name)
        if channel is None:
            print("[welcome] welcome channel not found")
            return

        perms = channel.permissions_for(member.guild.me)
        if not perms.send_messages:
            print("[welcome] no permission to send messages")
            return

        await channel.send(
            f"欢迎 {member.mention} 加入 🎉\n"
            f"输入 `/event create` 可以创建活动。"
        )

    @client.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        if message.content.strip().lower() == "ping":
            await message.channel.send("爱你哦（仅用于测试）")
