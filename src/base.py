# src/base.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import tasks


def _channel_url(guild_id: int, channel_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}"


def _parse_iso(dt_str: str, default_tz) -> datetime:
    d = datetime.fromisoformat(dt_str)
    if d.tzinfo is None:
        d = d.replace(tzinfo=default_tz)
    return d


def _get_ads_channel(
    guild: discord.Guild,
    *,
    channel_id: Optional[int],
    channel_name: Optional[str],
) -> Optional[discord.TextChannel]:
    if channel_id:
        ch = guild.get_channel(int(channel_id))
        return ch if isinstance(ch, discord.TextChannel) else None

    if channel_name:
        ch = discord.utils.get(guild.text_channels, name=channel_name)
        return ch

    return None


def register_base_events(client, config: dict):
    welcome_cfg = config.get("welcome", {})
    welcome_channel_name = welcome_cfg.get("channel_name")

    ads_cfg = config.get("ads", {})
    ads_enabled = bool(ads_cfg.get("enabled", False))
    ads_channel_id = ads_cfg.get("channel_id")
    ads_channel_name = ads_cfg.get("channel_name")
    ads_hour = int(ads_cfg.get("hour", 9))
    ads_minute = int(ads_cfg.get("minute", 0))
    blessing = (ads_cfg.get("blessing") or "").strip()

    _ads_started = False

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

        wcfg = config.get("welcome", {})
        primary_cmd = wcfg.get("primary_command") or "/event create"
        secondary_cmd = wcfg.get("secondary_command") or "/event list"
        # rules_name = (wcfg.get("rules_channel_name") or "").strip()
        # intro_name = (wcfg.get("intro_channel_name") or "").strip()

        # rules_ch = discord.utils.get(member.guild.text_channels, name=rules_name) if rules_name else None
        # intro_ch = discord.utils.get(member.guild.text_channels, name=intro_name) if intro_name else None

        lines = [
            f"🎉 欢迎 {member.mention} 来到 **{member.guild.name}**！",
            "先给你三条最省时间的上手路线：",
            f"1) 想发起活动：输入 `{primary_cmd}`",
            f"2) 想看看今天/近期活动：输入 `{secondary_cmd}`",
        ]

        # if rules_ch is not None:
        #     lines.append(f"3) 先看一下规则：{rules_ch.mention}")

        # if intro_ch is not None:
        #     lines.append(f"🙌 想认识大家可以去 {intro_ch.mention} 打个招呼～")

        lines.append("需要帮助就直接 @我，我不咬人（最多发日志）。")

        await channel.send("\n".join(lines))


    @client.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        content = (message.content or "").strip().lower()

        if content in {"ping", "p", "!ping"}:
            wcfg = config.get("welcome", {})
            primary_cmd = wcfg.get("primary_command") or "/event create"
            secondary_cmd = wcfg.get("secondary_command") or "/event list"

            await message.channel.send(
                "🏓 pong！爱你呦。\n"
                f"快速入口：`{primary_cmd}`（创建活动） / `{secondary_cmd}`（查看活动）"
            )
            return

        if content in {"早安", "早", "good morning"}:
            await message.channel.send("☀️ 早！今天也要把生活都跑通。")
            return

    # ===== Daily ads loop =====
    def _build_ads_message(guild: discord.Guild, now: datetime, events) -> str:
        lines = [f"📣 **{now.date().isoformat()} 今日活动**"]

        if not events:
            lines.append("- 今天暂无已发布活动 🤖")
        else:
            for e in events:
                try:
                    start_dt = _parse_iso(e.start_iso, now.tzinfo)
                    ts = int(start_dt.timestamp())  
                    ch_mention = f"<#{e.channel_id}>"
                    ch_url = _channel_url(guild.id, e.channel_id)

                    extras = []
                    if getattr(e, "channel_name", None):
                        extras.append(f"频道：{e.channel_name}")
                    if getattr(e, "member_limit", None) is not None:
                        extras.append(f"人数上限：{e.member_limit}")

                    extra_part = f"（{'，'.join(extras)}）" if extras else ""

                    lines.append(
                        f"- **{e.title}** • <t:{ts}:t> • {ch_mention} • {ch_url} {extra_part}".rstrip()
                    )
                except Exception:
                    lines.append("- （有一条活动信息格式不对，被我吞了）")

        if blessing:
            lines.append("")
            lines.append(f"✨ {blessing}")

        return "\n".join(lines)

    @tasks.loop(minutes=1)
    async def daily_ads_loop():
        if not ads_enabled:
            return

        now = client.time_now_func() if hasattr(client, "time_now_func") else datetime.now()

        if now.hour != ads_hour or now.minute != ads_minute:
            return

        if not getattr(client, "store", None):
            print("[ads] client.store not set")
            return

        for guild in client.guilds:
            channel = _get_ads_channel(
                guild,
                channel_id=int(ads_channel_id) if ads_channel_id else None,
                channel_name=ads_channel_name,
            )
            if channel is None:
                print(f"[ads] ads channel not found in guild={guild.name}")
                continue

            perms = channel.permissions_for(guild.me)
            if not perms.send_messages:
                print(f"[ads] no permission in #{channel.name} (guild={guild.name})")
                continue

            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            now_iso = now.isoformat()
            day_start_iso = day_start.isoformat()
            day_end_iso = day_end.isoformat()

            if not hasattr(client.store, "list_events_for_day"):
                print("[ads] store.list_events_for_day not implemented")
                continue

            try:
                events = client.store.list_events_for_day(
                    guild_id=guild.id,
                    day_start_iso=day_start_iso,
                    day_end_iso=day_end_iso,
                    now_iso=now_iso,
                    limit=50,
                )

                msg = _build_ads_message(guild, now, events)
                await channel.send(msg)
                print(f"[ads] sent daily ads to guild={guild.name} channel=#{channel.name}")

            except Exception as e:
                print(f"[ads] failed to send ads in guild={guild.name}: {e}")

    @daily_ads_loop.before_loop
    async def before_daily_ads_loop():
        await client.wait_until_ready()

    @client.event
    async def on_ready():
        nonlocal _ads_started
        if ads_enabled and not _ads_started:
            daily_ads_loop.start()
            _ads_started = True
            print(f"[ads] daily ads loop started at {ads_hour:02d}:{ads_minute:02d}")
