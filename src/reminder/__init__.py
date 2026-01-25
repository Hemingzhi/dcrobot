from discord import app_commands

from src.reminder.set import register_set
from src.reminder.list import register_list
from src.reminder.cancel import register_cancel


def register_reminder_commands(tree: app_commands.CommandTree, client) -> None:
    group = app_commands.Group(name="reminder", description="Reminder management")

    register_set(group, client)
    register_list(group, client)
    register_cancel(group, client)

    tree.add_command(group)
