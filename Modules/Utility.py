import nextcord
import asyncio

from utils import debug_command
from .abcModule import abcModule

class UtilityModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"commandslist": self.cmd_help,
                         "debug_getalltasks": self.dbgalltask}

    async def cmd_help(self, *args, channel, **_):
        em = nextcord.Embed(title="CPL Bot command list")
        for module in self.client.modules:
            cmds = " ".join([f"``{i}``" for i in module.commands.keys()])
            em.add_field(name=module.__class__.__name__,
                         value=cmds if cmds else "no commands",
                         inline=False)
        await channel.send(embed=em)

    @debug_command
    async def dbgalltask(self, *args, channel, **_):
        tasks = asyncio.all_tasks()
        tasks_str = '\n'.join(f"- {i}" for i in tasks)
        await channel.send(f"Running tasks ({len(tasks)}):\n{tasks_str}")