from discord import app_commands

from src.dashboard.me import register_me
from src.dashboard.server import register_server


def register_dashboard_commands(tree: app_commands.CommandTree, client) -> None:
    group = app_commands.Group(name="dashboard", description="Unified stats dashboard")

    register_me(group, client)
    register_server(group, client)

    tree.add_command(group)
