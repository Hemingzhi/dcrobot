from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord

from src.config_loading import load_config
from src.client import MyClient
from src.base import register_base_events
from src.event import register_event_commands

TIME_TZ = timezone(timedelta(hours=2))

def now_time() -> datetime:
    return datetime.now(tz=TIME_TZ)

def main():
    config = load_config()
    token = config["discord"]["token"]
    mode = (config.get("app", {}).get("mode") or "test").lower()

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    project_root = Path(__file__).resolve().parent

    client = MyClient(
        intents=intents,
        mode=mode,
        project_root=project_root,
        time_now_func=now_time,
    )

    register_event_commands(client.tree, client)
    register_base_events(client, config)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user} (id: {client.user.id}) | MODE={mode}")

    client.run(token)

if __name__ == "__main__":
    main()
