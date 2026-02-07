from discord import app_commands

from src.memo.add import register_add
from src.memo.list import register_list
from src.memo.done import register_done
from src.memo.show import register_show
from src.memo.reschedule import register_reschedule
from src.memo.cancel import register_cancel


def register_memo_commands(tree: app_commands.CommandTree, client) -> None:
    group = app_commands.Group(name="memo", description="Personal memo/todo")

    register_add(group, client)
    register_list(group, client)
    register_show(group, client)
    register_done(group, client)
    register_reschedule(group, client)
    register_cancel(group, client)

    tree.add_command(group)
