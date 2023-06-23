import nextcord
import asyncio
import logging
import traceback
from typing import Dict, List, Callable, Awaitable

from models.ReportParser import Match
from Database import Database
from FlaskServer import FlaskServer
from Modules import abcModule, DraftModule, RankedModule, RegisterModule, ReportModule, VotingModule, UtilityModule, TeamModule, BanModule, LobbyLinkModule
from config import COMMAND_PREFIX, DEVELOPPER_CONTACT, TOKEN_PATH, CPL_GUILD_ID, NO_COMMANDS_CHANNELS, SPECIFIC_CHANNEL_COMMAND
from exc import BotException, ALEDException, Forbidden

logger = logging.getLogger("Main")
logging.basicConfig(level=logging.INFO)

ACTIVE_MODULE = [DraftModule, RankedModule, ReportModule, VotingModule, UtilityModule, RegisterModule, TeamModule, LobbyLinkModule]

# Typing
COMMAND_T = Callable[[List[str]], Awaitable[None]]

class CPLBot(nextcord.Client):
    def __init__(self):
        super().__init__(allowed_mentions=nextcord.AllowedMentions(everyone=False), intents=nextcord.Intents.all())
        self.modules : List[abcModule] = []
        self.commands : Dict[str, COMMAND_T] = {}
        self.event: Dict[str, List[Callable]] = {}
        self.database : Database = Database()
        self.flaskServer : FlaskServer = FlaskServer(self)

    def run_flask_server(self):
        logger.info("Running Flask Server")
        self.flaskServer.start()

    async def load_modules(self):
        logger.info("Loading modules ...")
        for moduleClass in ACTIVE_MODULE:
            logger.info(f"Loading module: {moduleClass.__name__}")
            module = moduleClass(client=self)
            self.modules.append(module)
            asyncio.create_task(module.on_ready())
            self.commands.update(module.commands)
            for k, v in module.events.items():
                self.event[k] = self.event.get(k, []) + v

    def get_module(self, module_cls):
        for module in self.modules:
            if isinstance(module, module_cls):
                return module
        return None

    async def process_command(self, message):
        args = message.content.split(' ')
        command = args[0][len(COMMAND_PREFIX):].lower()
        func = self.commands.get(command, None)
        if func is None:
            return
        try:
            if message.channel.id in NO_COMMANDS_CHANNELS:
                raise Forbidden("Commands are not allowed in this channel")
            cmd_specific_channels = SPECIFIC_CHANNEL_COMMAND.get(command, None)
            if cmd_specific_channels is not None and message.channel.id not in cmd_specific_channels and message.guild == CPL_GUILD_ID:
                raise Forbidden("This command can only be used in following channels : " + ' '.join(f"<#{i}>" for i in cmd_specific_channels))
            await func(*args[1:], message=message, member=message.author, channel=message.channel,
                       guild=message.guild, client=self)
        except ALEDException as e:
            await message.channel.send(f"A Fatal error occured, please contact {DEVELOPPER_CONTACT}:"
                                       f"```diff\n-[FATAL ERROR]\n{traceback.format_exc()}```")
        except BotException as e:
            await message.channel.send(f"{type(e).__name__}: {e}")
        except Exception as e:
            await message.channel.send(
                f"An unexcepted exception occured:```diff\n-[ERROR]\n{traceback.format_exc()}```")

    async def on_ready(self):
        self.run_flask_server()
        await self.load_modules()
        logger.info(f"Connected as {self.user}")

    async def on_message(self, message : nextcord.Message):
        if message.content.startswith(COMMAND_PREFIX):
            await self.process_command(message)
        await asyncio.gather(*(func(message) for func in self.event.get('on_message', [])))

    async def on_raw_message_edit(self, payload : nextcord.RawMessageUpdateEvent):
        if payload.cached_message and payload.cached_message.author == self.user:
            return
        await asyncio.gather(*(func(payload) for func in self.event.get('on_edit', [])))

    async def on_raw_message_delete(self, payload : nextcord.RawMessageDeleteEvent):
        if payload.cached_message and payload.cached_message.author == self.user:
            return
        await asyncio.gather(*(func(payload) for func in self.event.get('on_delete', [])))

    async def on_raw_reaction_add(self, payload : nextcord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        await asyncio.gather(*(func(payload) for func in self.event.get('on_reaction_add', [])))

    async def on_raw_reaction_remove(self, payload : nextcord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return
        await asyncio.gather(*(func(payload) for func in self.event.get('on_reaction_remove', [])))

    async def on_reaction_add(self, reaction : nextcord.Reaction, user : nextcord.User):
        if user.id == self.user.id:
            return
        await asyncio.gather(*(func(reaction, user) for func in self.event.get('on_live_reaction_add', [])))

    async def on_validate_match(self, match : Match):
        await asyncio.gather(*(func(match) for func in self.event.get('on_validate_match', [])))

    @property
    def cpl_guild(self) -> nextcord.Guild:
        return self.get_guild(CPL_GUILD_ID)

    def run(self):
        with open(TOKEN_PATH) as fd:
            _token = fd.read()
        super().run(_token)


if __name__ == '__main__':
    cplbot = CPLBot()
    cplbot.run()