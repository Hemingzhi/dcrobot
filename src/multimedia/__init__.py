from discord import app_commands

from src.multimedia.add import register_add
from src.multimedia.list import register_list
from src.multimedia.watch import register_watch
from src.multimedia.unwatch import register_unwatch
from src.multimedia.my import register_my
from src.multimedia.stats import register_stats
from src.multimedia.delete_item import register_delete_item


def register_multimedia_commands(tree: app_commands.CommandTree, client) -> None:
    group = app_commands.Group(name="multimedia", description="Multimedia management")

    register_add(group, client)
    register_list(group, client)
    register_watch(group, client)
    register_unwatch(group, client)
    register_my(group, client)
    register_stats(group, client)
    register_delete_item(group, client)

    tree.add_command(group)
