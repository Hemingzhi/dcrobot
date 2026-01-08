from discord import app_commands

from src.event.create import register_create
from src.event.list import register_list


def register_event_commands(tree: app_commands.CommandTree, client):
    group = app_commands.Group(name="event", description="Event management")

    register_create(group, client)
    register_list(group, client)

    tree.add_command(group)
