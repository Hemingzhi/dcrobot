from datetime import datetime, timedelta

import discord
from discord import app_commands

from src.channel import create_text_channel, create_voice_channel, get_or_create_category
from src.restrictions import only_in_event_create_channel


def _parse_dt(dt_str: str, tzinfo) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=tzinfo)


def register_create(group: app_commands.Group, client):
    async def category_autocomplete(interaction: discord.Interaction, current: str):
        if interaction.guild is None:
            return []

        db_names = client.store.list_category_options(guild_id=interaction.guild.id, limit=25)
        guild_names = [c.name for c in interaction.guild.categories]
        names = sorted(set(db_names + guild_names))

        cur = (current or "").lower()
        matched = [n for n in names if cur in n.lower()][:25]
        return [app_commands.Choice(name=n, value=n) for n in matched]

    async def channel_type_autocomplete(interaction: discord.Interaction, current: str):
        options = ["text", "voice"]
        cur = (current or "").lower()
        matched = [o for o in options if cur in o][:25]
        return [app_commands.Choice(name=o, value=o) for o in matched]

    @group.command(name="create", description="Create a new event")
    @only_in_event_create_channel(client)
    @app_commands.autocomplete(category=category_autocomplete, channel_type=channel_type_autocomplete)
    @app_commands.describe(
        title="Event title",
        start="Start time (YYYY-MM-DD HH:MM, local time)",
        end="End time (optional)",
        description="Optional description",
        create_channel="Create a dedicated channel for this event",
        channel_type="Channel type: text or voice (default: text)",
        channel_name="New channel name (optional). If empty, it uses the title",
        member_limit="Max participants (optional). For voice channel: user limit",
        category="Category name for the created channel (optional, can be new)",
    )
    async def create(
        interaction: discord.Interaction,
        title: str,
        start: str,
        end: str | None = None,
        description: str | None = None,
        create_channel: bool = False,
        channel_type: str = "text",
        channel_name: str | None = None,
        member_limit: int | None = None,
        category: str | None = None,
    ):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        title = title.strip()
        if len(title) < 2:
            await interaction.response.send_message("Title too short.", ephemeral=True)
            return

        if member_limit is not None and (member_limit < 1 or member_limit > 99):
            await interaction.response.send_message("member_limit must be between 1 and 99.", ephemeral=True)
            return

        channel_type = (channel_type or "text").strip().lower()
        if channel_type not in ("text", "voice"):
            await interaction.response.send_message("channel_type must be 'text' or 'voice'.", ephemeral=True)
            return

        if not create_channel and (category or channel_name or channel_type != "text" or member_limit is not None):
            await interaction.response.send_message(
                "category/channel_name/channel_type/member_limit are only used when create_channel=true.",
                ephemeral=True,
            )
            return

        try:
            tzinfo = client.now_time().tzinfo
            start_dt = _parse_dt(start.strip(), tzinfo)
            end_dt = _parse_dt(end.strip(), tzinfo) if end else None
        except ValueError:
            await interaction.response.send_message("Invalid time format. Use YYYY-MM-DD HH:MM.", ephemeral=True)
            return

        if end_dt and end_dt <= start_dt:
            await interaction.response.send_message("End time must be after start time.", ephemeral=True)
            return

        expires_dt = end_dt if end_dt else start_dt + (timedelta(minutes=10) if client.mode == "test" else timedelta(days=7))

        created_channel = None
        used_category_name = None

        if create_channel:
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if member is None:
                await interaction.response.send_message("Cannot resolve member.", ephemeral=True)
                return

            cat_obj = None
            if category and category.strip():
                used_category_name = category.strip()
                try:
                    cat_obj = await get_or_create_category(guild=interaction.guild, name=used_category_name)
                    client.store.add_category_option(guild_id=interaction.guild.id, name=used_category_name)
                except PermissionError:
                    await interaction.response.send_message(
                        "I don't have permission to create categories/channels. Please grant me **Manage Channels**.",
                        ephemeral=True,
                    )
                    return
                except Exception as e:
                    await interaction.response.send_message(f"Failed to prepare category: {e}", ephemeral=True)
                    return

            try:
                final_name = channel_name.strip() if channel_name else title

                if channel_type == "voice":
                    created_channel = await create_voice_channel(
                        guild=interaction.guild,
                        requester=member,
                        name=final_name,
                        category=cat_obj,
                        user_limit=member_limit,
                    )
                else:
                    created_channel = await create_text_channel(
                        guild=interaction.guild,
                        requester=member,
                        name=final_name,
                        category=cat_obj,
                        topic=description,
                    )
            except PermissionError:
                await interaction.response.send_message(
                    "I don't have permission to create channels. Please grant me **Manage Channels**.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                await interaction.response.send_message(f"Failed to create channel: {e}", ephemeral=True)
                return

        ev = client.store.create_event(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            title=title,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat() if end_dt else None,
            description=description,
            created_by=interaction.user.id,
            expires_at=expires_dt.isoformat(),
            channel_name=(created_channel.name if created_channel else None),  # 用于过期自动删除
            member_limit=member_limit if create_channel and channel_type == "voice" else member_limit,
        )

        display_channel = created_channel or interaction.channel

        embed = discord.Embed(title=f"✅ Event created: {ev.title}")
        embed.add_field(name="Start", value=start_dt.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="End", value=(end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else "—"), inline=True)
        embed.add_field(name="Expires", value=expires_dt.strftime("%Y-%m-%d %H:%M"), inline=False)

        if created_channel:
            embed.add_field(name="Channel", value=display_channel.mention, inline=False)
            embed.add_field(name="Channel type", value=channel_type, inline=True)
        else:
            embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)

        if used_category_name:
            embed.add_field(name="Category", value=used_category_name, inline=True)

        if member_limit is not None:
            if create_channel and channel_type == "voice":
                embed.add_field(name="Voice user limit", value=str(member_limit), inline=True)
            else:
                embed.add_field(name="Max participants (rule)", value=str(member_limit), inline=True)

        if description:
            embed.add_field(name="Description", value=description, inline=False)

        embed.set_footer(text=f"Event ID: {ev.id}")

        channel_url = f"https://discord.com/channels/{interaction.guild.id}/{display_channel.id}"
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Go to channel",
                style=discord.ButtonStyle.link,
                url=channel_url,
            )
        )

        if created_channel:
            await created_channel.send(embed=embed, view=view)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
