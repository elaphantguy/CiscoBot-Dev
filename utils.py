import nextcord
import re
from typing import Optional, List
from datetime import datetime, timezone

from config import MODERATOR_ROLE_ID, CPL_GUILD_ID, CAN_USE_DBG_COMMAND, CAN_USE_ADMIN_COMMAND
from exc import Forbidden, NotFound, ALEDException

def get_member_by_name(name, ctx) -> Optional[nextcord.Member]:
    if isinstance(ctx, nextcord.Guild):
        member = ctx.get_member_named(name)
        if member:
            return member
        if name.isdigit():
            return ctx.get_member(int(name))
        match = re.findall(r"<@!?(\d+)>", name)
        if match:
            return ctx.get_member(int(match[0]))
    elif isinstance(ctx, nextcord.Client):
        if name.isdigit():
            return ctx.get_user(int(name))
        match = re.findall(r"<@!?(\d+)>", name)
        if match:
            return ctx.get_user(int(match[0]))
    else:
        raise ALEDException("Unkown context in get_member_by_name: " + type(ctx).__name__)
    return None

def get_discord_id_from_date(date : datetime) -> int:
    time_between_discord_epoch = date - datetime(2015, 1, 1, tzinfo=timezone.utc)
    return int(time_between_discord_epoch.total_seconds() * 1000) << 22

def get_member_in_channel(voice : nextcord.VoiceState) -> List[nextcord.Member]:
    if not voice or not voice.channel:
        raise NotFound("Can't get player list : You are not connected to a channel")
    return voice.channel.members

def is_moderator(member : nextcord.Member, client=None) -> bool:
    if not isinstance(member, nextcord.Member):
        if not client:
            return False
        guild = client.get_guild(CPL_GUILD_ID)
        member = guild.get_member(member.id)
        if not member:
            return False
    return (MODERATOR_ROLE_ID in [i.id for i in member.roles]) or member.id == 384274248799223818

def can_use_dbg_commands(member : nextcord.Member, client=None) -> bool:
    if not isinstance(member, nextcord.Member):
        if not client:
            return False
        guild = client.get_guild(CPL_GUILD_ID)
        member = guild.get_member(member.id)
    for role in member.roles:
        if role.id in CAN_USE_DBG_COMMAND:
            return True
    return False

def can_use_admin_commands(member : nextcord.Member, client=None) -> bool:
    if not isinstance(member, nextcord.Member):
        if not client:
            return False
        guild = client.get_guild(CPL_GUILD_ID)
        member = guild.get_member(member.id)
    for role in member.roles:
        if role.id in CAN_USE_ADMIN_COMMAND:
            return True
    return False

def moderator_command(func):
    async def wrapper(self, *args, member, client, **kwargs):
        if is_moderator(member, client):
            await func(self, *args, member=member, client=client, **kwargs)
        else:
            raise Forbidden("You need to be moderator to use this command")
    return wrapper

def debug_command(func):
    async def wrapper(self, *args, member, client, **kwargs):
        if can_use_dbg_commands(member, client):
            await func(self, *args, member=member, client=client, **kwargs)
        else:
            raise Forbidden("You don't have permission to use debug commands")
    return wrapper

def admin_command(func):
    async def wrapper(self, *args, member, client, **kwargs):
        if can_use_admin_commands(member, client):
            await func(self, *args, member=member, client=client, **kwargs)
        else:
            raise Forbidden("You don't have permission to use admin commands")
    return wrapper