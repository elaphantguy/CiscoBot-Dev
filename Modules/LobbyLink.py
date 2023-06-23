import nextcord
import urllib.parse
from config import SERVER_IP, SERVER_PORT

from .abcModule import abcModule
from exc import BotException

class LobbyLinkModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"lobbylink": self.cmd_lobbylink}

    async def cmd_lobbylink(self, *args : str, channel, message, member, **_):
        if len(args) < 1:
            raise BotException("Invalid number of arguments. Usage: `.lobbylink <lobby link> [host rules]`")

        lobby_link = args[0]
        host_rules = " ".join(args[1:])

        link = LobbyLink(channel)
        await link.run(lobby_link, message, host_rules)

class LobbyLink:
    def __init__(self, channel : nextcord.TextChannel):
        self.channel = channel

    def __repr__(self):
        return f"Link({self.members}, {self.channel})"

    async def run(self, lobby_link : str, message : nextcord.Message, host_rules : str):
        if not lobby_link.startswith('steam://joinlobby/'):
            raise BotException("Invalid lobby link. Usage: `lobbylink <lobby link>(steam://joinlobby/...)`")

        link = removeprefix(lobby_link, 'steam://joinlobby/')
        embed = nextcord.Embed(
            title=f"Join {message.author.name}'s Lobby",
            description=f"Lobby Link: [Steam Lobby](http://{SERVER_IP}:{SERVER_PORT}/join/{link})",
            color=0x00ff00,
            url=f"http://{SERVER_IP}:{SERVER_PORT}/join/{urllib.parse.quote(link)}"
        )

        if host_rules.strip():
            embed.add_field(name="Host Rules", value=host_rules, inline=False)

        embed.set_footer(text="Powered by CPL Bot")
        await self.channel.send(embed=embed)
        await message.delete()

def removeprefix(message: str, prefix: str):
    if message.startswith(prefix):
        return message[len(prefix):]
    return message