from __future__ import annotations

import discord
from discord import app_commands


def register_list(group: app_commands.Group, client) -> None:
    @group.command(name="list", description="List your memo items")
    @app_commands.describe(status="open/done/canceled", limit="1-20")
    async def list_cmd(
        interaction: discord.Interaction,
        status: str = "open",
        limit: int = 10,
    ):
        if interaction.guild is None or interaction.user is None:
            await interaction.response.send_message("Please use this in a server channel.", ephemeral=True)
            return

        status = (status or "open").strip().lower()
        if status not in ("open", "done", "canceled"):
            await interaction.response.send_message("status must be open/done/canceled.", ephemeral=True)
            return

        limit = max(1, min(int(limit), 20))

        items = client.store.list_memo_items(
            guild_id=interaction.guild.id,
            owner_user_id=interaction.user.id,
            status=status,
            limit=limit,
            offset=0,
        )

        if not items:
            await interaction.response.send_message(f"No {status} memo items.", ephemeral=True)
            return

        lines = []
        for m in items:
            extra = []
            if m.due_at_iso:
                extra.append(f"due={m.due_at_iso}")
            if m.remind_at_iso and m.status == "open":
                extra.append(f"remind={m.remind_at_iso}")
            extra_s = (" | " + ", ".join(extra)) if extra else ""
            lines.append(f"`#{m.id}` **[{m.item_type}]** {m.title}{extra_s}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)
