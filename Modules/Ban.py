import nextcord
from datetime import datetime, timedelta, timezone

from .abcModule import abcModule
from models.DbModel import Suspension
from models.ReportParser import Match
from utils import get_member_by_name, moderator_command
from exc import NotFound, InvalidArgs, ModuleInitFailed
from config import *

class BanModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"suspensionstatus": self.cmd_suspension_status}
        # self.events = {"on_validate_match": [self.on_validate_match]}
        self.channel = self.client.get_channel(SUSPENDED_PLAYER_CHANNEL_ID)
        if not self.channel:
            raise ModuleInitFailed(f"Can't find channel ID {SUSPENDED_PLAYER_CHANNEL_ID}")
        self.suspended_role = self.client.get_guild(CPL_GUILD_ID).get_role(SUSPENDED_ROLE_ID)
        if not self.suspended_role:
            raise ModuleInitFailed(f"Can't find role ID {SUSPENDED_ROLE_ID} in guild {self.client.get_guild(CPL_GUILD_ID)}")
        self.great_people_role = self.client.get_guild(CPL_GUILD_ID).get_role(GREAT_PEOPLE_ROLE_ID)

    async def cmd_suspension_status(self, *args, guild, member, channel, **_):
        if args:
            target_name = ' '.join(args)
            target = get_member_by_name(target_name, guild or self.client)
            if not target:
                raise NotFound(f"Member \"{target_name}\" not found")
        else:
            target = member

        suspenstion = self.database.get_suspension(target.id)
        if suspenstion:
            await channel.send(embed=suspenstion.to_embed())
        else:
            await channel.send(f"No Suspension that found for player <@{target.id}>")

    async def add_suspended_role(self, member : nextcord.Object) -> bool:
        try:
            if not isinstance(member, nextcord.Member):
                member = self.client.get_guild(CPL_GUILD_ID).get_member(member.id)
            await member.add_roles(self.suspended_role, reason="Added by Ban Bot")
            return True
        except nextcord.HTTPException:  # Mostly raised because player left the guild
            return False

    async def apply_punishment(self, target : nextcord.Object, tier : str, author : nextcord.User, reason : str = None):
        suspension = self.database.get_suspension(target.id)
        tier_nb = SUSPENSIONS_TYPE_TIERS.get(tier, None)
        if tier_nb is None:
            raise InvalidArgs(f"Suspension type \"{tier}\" don't exist")
        if not QUIT_APPLY_BASIC_SUSPENSION and tier == "quit":
            suspension.quit_tier += tier_nb
            tier = suspension.quit_tier
        else:
            suspension.tier += tier_nb
            tier = suspension.tier
        suspension.game_without_penalty = 0
        suspension_time = SUSPENSION_TIME[tier - 1 if tier < len(SUSPENSION_TIME) else -1]
        new_end = datetime.now(tz=timezone.utc) + timedelta(days=suspension_time)
        if not suspension.end or new_end > suspension.end:
            suspension.end = new_end
        suspension.next_decay_games = GAME_TO_DECAY_TIER
        suspension.next_decay_timestamp = suspension.end + TIME_TO_DECAY_TIER
        ban_msg = f"**[ <@{target.id}> {tier.upper()} INFRACTION ({tier_nb} tier{'s' if tier_nb < 1 else ''}) ]**\n"
        if reason:
            ban_msg += f"**REASON:** {reason}\n"
        ban_msg = f"Your {'quit' if not QUIT_APPLY_BASIC_SUSPENSION and tier == 'quit' else 'suspension'} tier is now {tier}."
        if suspension_time < DAY_TO_PERMA:
            ban_msg += f"**RESULT:** {suspension_time} day{'s' if suspension_time > 1 else ''} suspension.\n"
        else:
            ban_msg += "**RESULT:** Perma banned from CPL."
        ban_msg += f"**END:** " + suspension.end.strftime("%A %d %B %Y at %H:%M %Z")
        history_msg = f"{datetime.now(tz=timezone.utc).strftime('%A %d %B %Y at %H:%M:%S %Z')}: {tier} infraction - by <@{author.name}>"
        if reason:
            history_msg += ". Reason: " + reason
        suspension.history.append(history_msg)
        if suspension_time:
            suspension.is_suspended = True
            self.database.set_suspension(suspension)
            await self.add_suspended_role(target)
        await self.channel.send(ban_msg)

    async def check_and_apply_decay(self, suspension : Suspension):
        if not suspension.can_decay():
            return
        txt = ""
        if suspension.tier > 0:
            suspension.tier -= 1
            txt += f"\nSuspension tier is now {suspension.tier}"
        if not QUIT_APPLY_BASIC_SUSPENSION and suspension.quit_tier > 0:
            suspension.quit_tier -= 1
            txt += f"\nQuit tier is now {suspension.quit_tier}"
        if not txt:  # No tier decay
            return
        # Set new goal
        if suspension.tier or (suspension.quit_tier and not QUIT_APPLY_BASIC_SUSPENSION):
            suspension.next_decay_games += GAME_TO_DECAY_TIER
            suspension.next_decay_timestamp += TIME_TO_DECAY_TIER
        else:
            suspension.next_decay_games = None
            suspension.next_decay_timestamp = None
        # Send message
        await self.channel(f"**[ <@{suspension.id}> Tier Decay ]**" + txt)
        # Save in database
        self.database.set_suspension(suspension)

    async def check_and_apply_great_people(self, suspension : Suspension):
        try:
            if suspension.is_great_people():
                member = self.client.get_guild(CPL_GUILD_ID).get_member(suspension.id)
                if not member or self.great_people_role in member.roles:
                    return
                await member.add_roles(self.great_people_role, reason="Added by BanBot")
        except nextcord.HTTPException:
            return

    async def on_validate_match(self, match : Match):
        for player in match.players:
            if REPORT_APPLY_QUIT and "QUIT" in player.flags:
                await self.apply_punishment(nextcord.Object(player.id), "quit", self.client.user, reason="Automatic quit")
                continue
            if REPORT_APPLY_OVERSUB and "SUBBED" in player.flags:
                plstat = self.database.get_playerstats_by_id(match.gametype.value, player.id)
                if plstat.is_oversub():
                    await self.apply_punishment(nextcord.Object(player.id), OVERSUB_PENALTY_TIER, self.client.user, reason="Subbed without sub token")
                continue
            suspension = self.database.get_suspension(player.id)
            suspension.game_without_penalty += 1
            await self.check_and_apply_decay(suspension)
            await self.check_and_apply_great_people(suspension)
            self.database.set_suspension(suspension)


    @moderator_command
    async def cmd_minor(self, *args):
        ...