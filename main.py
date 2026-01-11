from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord

from src.base import register_base_events
from src.client import MyClient
from src.config_loading import load_config
from src.event import register_event_commands
from src.category import register_category_commands


def main():
    config = load_config()
    token = config["discord"]["token"]
    mode = (config.get("app", {}).get("mode") or "test").lower()

    default_tz_name = config.get("time", {}).get("default_tz", "Europe/Paris")
    default_tz = ZoneInfo(default_tz_name)

    def now_time() -> datetime:
        return datetime.now(tz=default_tz)

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    project_root = Path(__file__).resolve().parent

    client = MyClient(
        intents=intents,
        mode=mode,
        project_root=project_root,
        time_now_func=now_time,
        config=config,
    )

    register_event_commands(client.tree, client)
    register_category_commands(client.tree, client)  
    register_base_events(client, config)

    @client.event
    async def on_ready():
        print(
            f"Logged in as {client.user} (id: {client.user.id}) | MODE={mode} | TZ={default_tz_name}"
        )

    client.run(token)


if __name__ == "__main__":
    main()
