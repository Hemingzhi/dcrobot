from __future__ import annotations

from discord import app_commands

from src.category.create import register_category_create
from src.category.delete import register_category_delete
from src.category.list import register_category_list
from src.category.purge import register_category_purge

def register_category_commands(tree: app_commands.CommandTree, client) -> None:
    category_group = app_commands.Group(name="category", description="Manage categories")
    tree.add_command(category_group)

    register_category_create(category_group, client)
    register_category_list(category_group, client)
    register_category_delete(category_group, client)
    register_category_purge(category_group, client)


__all__ = ["register_category_commands"]
