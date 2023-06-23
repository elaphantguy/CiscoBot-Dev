import nextcord
from typing import List
import random

from .abcModule import abcModule
from exc import BotException, BusyException
from utils import get_member_in_channel

class TeamModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"teamgen": self.cmd_gen}
        self._running_instances : List[Team]

    async def cmd_gen(self, *args : str, channel, member, message, **_):
        members = await self.parse_args(args, channel, member, message)
        team = Team(members, channel)
        await team.run(channel)

    @staticmethod
    async def parse_args(args, channel, member, message):
        if not args:
            members = get_member_in_channel(member.voice)
        else:
            try:
                members = get_member_in_channel(member.voice)
            except:
                members = []
            diff_members = message.mentions
            added = []
            removed = []
            for member in diff_members:
                if member in members:
                    removed.append(member)
                    members.remove(member)
                else:
                    added.append(member)
                    members.append(member)
            if removed:
                await channel.send("The following player has been removed from the vote: " + ', '.join(i.mention for i in removed))
            if added:
                await channel.send("The following player has been added to the vote: " + ', '.join(i.mention for i in added))
        if not members:
            raise BotException("Trying to run a vote without members")
        return members

class Team:
    def __init__(self, members, channel):
      self.channel = channel
      self.members = members

    def __repr__(self):
        return f"<TeamGen members={self.members}>"

    async def run(self, channel : nextcord.TextChannel):
        await channel.send("Team Gen is in progress ...")
        if len(self.members) < 2:
            await channel.send("Not enough players to form two teams.")
            return
        
        random.shuffle(self.members)
        team_size = len(self.members) // 2
        team1 = self.members[:team_size]
        team2 = self.members[team_size:]

        embed = nextcord.Embed(title="Random Teams", color=0x006dff)
        embed.add_field(name="Team 1", value='\n'.join(i.mention for i in team1))
        embed.add_field(name="Team 2", value='\n'.join(i.mention for i in team2))
        await channel.send(embed=embed)