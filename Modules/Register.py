import nextcord
import aiohttp

from config import OAUTH_LINK_BASE, WELCOME_CHANNEL, NEW_REGISTERED_LOG_CHANNEL, ROLES_WHEN_REGISTED
from utils import moderator_command
from .abcModule import abcModule


class RegisterModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"register": self.cmd_register,
                         "check_sharing": self.cmd_check_sharing}
        self.welcome_channel = client.get_channel(WELCOME_CHANNEL)
        self.new_registered_log_channel = client.get_channel(NEW_REGISTERED_LOG_CHANNEL)
        with open("private/steam_creds") as fd:
            self._api_key = fd.read()

    async def register_player(self, discord_id : str, steam_id : str):
        cpl : nextcord.Guild = self.client.cpl_guild
        member : nextcord.Member = cpl.get_member(int(discord_id))
        player = self.database.register_player(discord_id, steam_id, member.name)
        await self.welcome_channel.send(f"{member.mention}, you are now registered\nPlease read <#550251325724557322> and <#553224175398158346>")
        roles = [cpl.get_role(i) for i in ROLES_WHEN_REGISTED]
        await member.add_roles(*roles, reason="Registered")
        await self.new_registered_log_channel.send(f"Discord ID: {discord_id} (<@{discord_id}>)\nSteam ID: {steam_id}")

    async def cmd_register(self, *args, channel, member, **_):
        player = self.database.get_player_by_discord_id(member.id)
        if player is not None:
            await channel.send("Error: You are already registered", embed=player.to_embed())
            return
        em = nextcord.Embed(title="Authorize Bot", colour=0X0099FF,
                           description=f"The CPL Bot needs authorization in order to search your Discord profile for your linked Steam account. It uses Steam accounts to verify unique users.\n\n[Click here to authorize]({OAUTH_LINK_BASE}{member.id})")
        em.set_footer(text="If you don't see the link, please turn on 'Link Preview' in your 'Text & Images' Discord Settings, then try aggain.")
        await channel.send(embed=em)

    @moderator_command
    async def cmd_check_sharing(self, *args, channel, **_):
        target = args[0]
        if '/' in target:
            target = target.strip().strip('/')
            target = args[0].rsplit('/', 1)[1]
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"https://steamid.io/lookup/{target}")
            response_content : bytes = await response.read()
            steamid64 = int(response_content.split(b'data-steamid64', 1)[1].split(b'"')[1])
            response = await session.get("https://api.steampowered.com/IPlayerService/IsPlayingSharedGame/v0001/",
                                         params={'key': self._api_key, 'steamid': steamid64, 'appid_playing': 289070})
            json = await response.json(encoding='utf_8')
            lender_id = json['response'].get('lender_steamid', '0')
            txt = f"Check Status Sharing for query \"{target}\", SteamID64: {steamid64}\nResult:\n"
            if lender_id == '0':
                await channel.send(txt + "if they have the game open now, it's not a shared copy")
            else:
                await channel.send(txt + "Lender's steam link: <https://steamcommunity.com/profiles/" + lender_id + ">")