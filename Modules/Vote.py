import nextcord
import asyncio
import logging
import time
from typing import Iterable, List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta, timezone

from .abcModule import abcModule
from Leaders import leaders, Leader
from exc import InvalidArgs, Timeout, BotException, BusyException
from utils import get_member_in_channel, debug_command
from config import SECRET_REMAP_VOTE_SETTING, VOTE_SETTINGS, DEFAULT_VOTE_SETTINGS, SECRET_CC_VOTE_SETTINGS, SECRET_SCRAP_VOTE_SETTINGS, SECRET_IRREL_VOTE_SETTINGS, TEAM_VOTE_SETTINGS, DraftMode, DRAFT_MODE_TITLE, MINUTES_BEFORE_REMOVING_VOTE
from constant import EMOJI_PLUS, EMOJI_CROWN, EMOJI_OK

from .Draft import DraftModule, BlindDraft, DynamicDraft

EMOJI = str
logger = logging.getLogger("VoteModule")

class VotingModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"vote": self.cmd_vote,
                         "teamvote": self.cmd_teamvote,
                         "secretvote": self.cmd_secretvote,
                         "dbgrunningvoteinstance": self.dbgrunningvoteinstance}
        self.dependency = [DraftModule]
        self.events = {"on_live_reaction_add": [self.on_reaction_add]}
        self._running_instances : List[Voting] = []

    async def cmd_vote(self, *args : str, channel, member, message, **_):
        members = await self.parse_args(args, channel, member, message)
        voting = Voting(members, VOTE_SETTINGS, DEFAULT_VOTE_SETTINGS, channel)
        self._running_instances.append(voting)
        await voting.run(channel, self.client)

    async def cmd_secretvote(self, *args : str, channel, member, message, **_):
        if not args:
            raise InvalidArgs("You must supply a vote type, cc, scrap, irrel or remap")
        elif args[0] not in ("cc", "irrel", "scrap","remap"):
            raise InvalidArgs("Vote type must be either cc, scrap or irrel")
        elif len(args) < 2:
            raise InvalidArgs("You must supply a civilization, player, cc order or turn number")
        members = await self.parse_args(args, channel, member, message)
        msg = []
        for word in args[2:]:
            if not word.startswith("<@"):
                msg.append(word)
        string = ' '.join(msg)
        voting = SecretVote(args[0], args[1], members, {
            "cc": SECRET_CC_VOTE_SETTINGS,
            "remap": SECRET_REMAP_VOTE_SETTING,
            "scrap": SECRET_SCRAP_VOTE_SETTINGS,
            "irrel": SECRET_IRREL_VOTE_SETTINGS
        }, channel, string)
        self._running_instances.append(voting)
        await voting.run(channel)


    async def cmd_teamvote(self, *args : str, channel, member, message, **_):
        members = await self.parse_args(args, channel, member, message)
        voting = Voting(members, TEAM_VOTE_SETTINGS, DEFAULT_VOTE_SETTINGS, channel, is_team=True)
        self._running_instances.append(voting)
        await voting.run(channel, self.client)

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


    @debug_command
    async def dbgrunningvoteinstance(self, *_args : str, channel, **_):
        await channel.send(f"Current running Voting instance ({len(self._running_instances)}) : {self._running_instances}")

    @debug_command
    async def dbgpurgevoteinstance(self, *_args : str, channel, **_):
        self._running_instances = []
        await self.dbgrunningvoteinstance(channel=channel)

    async def on_reaction_add(self, reaction : nextcord.Reaction, user : nextcord.User):
        for instance in self._running_instances:
            asyncio.create_task(self._on_reaction_add(instance, reaction, user))

    async def _on_reaction_add(self, instance, reaction, user):
        while instance.has_confirm == True and instance.confirm_msg is None:
            if datetime.now(tz=timezone.utc) > instance.created_at + timedelta(minutes=2):
                print("Instance not ready after 2 minutes, deleting event")
                self._running_instances.remove(instance)
                return
            print("Instance not ready, waiting 5 secondes ...")
            await asyncio.sleep(5)
        if await instance.on_reaction_add(reaction, user, self.client):
            self._running_instances.remove(instance)


class Voting:
    _instance_busy = False

    DRAFT_MODE_TITLE = "Draft Mode"
    class DraftMode(Enum):
        WITH_TRADE = "Trade Allowed"
        NO_TRADE = "Trade Forbidden"
        BLIND = "Blind"
        RANDOM = "All Random"

    def __init__(self, members, vote_settings, default_vote_settings, channel, is_team=False):
        self.is_team = is_team
        self._vote_settings = vote_settings
        self._default_vote_settings = default_vote_settings
        self.members = members
        self.members_id = [i.id for i in members]
        self.waiting_members = self.members_id[:]
        self.result = {i: None for i in vote_settings}
        self.msg_ids = []
        self.majority = len(self.members) // 2 + 1
        self.banned_leaders = []
        self.draft_mode = None

        self.sended = None
        self.defaults = None
        self.ban_msg = None
        self.confirm_msg = None
        self.votes_msg_ids = None
        self.msg_to_vote = None
        self.has_confirm = True

        self.channel = channel
        self.created_at = datetime.now(tz=timezone.utc)
        self.delete_at = self.created_at + timedelta(minutes=MINUTES_BEFORE_REMOVING_VOTE)

    def __repr__(self):
        return f"<Voting confirm_msg={self.confirm_msg.id}, ban_msg={self.ban_msg.id}, members={self.members}, waiting_members={self.waiting_members}>"

    async def run(self, channel : nextcord.TextChannel, client : nextcord.Client):
        self.check_if_instance_is_busy()
        Voting._instance_busy = True
        try:
            await channel.send(f"Player list ({len(self.members)}): " + ' '.join(i.mention for i in self.members))
            self.sended = await asyncio.gather(*[self.send_line(k, v, channel) for k, v in self._vote_settings.items()])
            await self.channel.send('\n'.join(f"{k}: {v}" for k, v in self._default_vote_settings.items()))
            self.ban_msg = await self.send_ban_msg(channel)
            self.confirm_msg = await self.send_confirm_msg(channel)
        except Exception as e:
            raise BotException from e
        finally:
            Voting._instance_busy = False
        self.votes_msg_ids = [i.id for i in self.sended]
        self.msg_ids = [*self.votes_msg_ids, self.ban_msg.id, self.confirm_msg.id]
        self.msg_to_vote : Dict[int, Tuple[str, List[Tuple[EMOJI, str]]]] = {self.sended[i].id: (name, v) for i, (name, (v)) in enumerate(self._vote_settings.items())}


    async def run_draft(self, client):
        if not self.draft_mode:
            await self.channel.send("WARNING : No drafting vote has been voted, a classic draft will be run.")
            self.draft_mode = DraftMode.DRAFT_2 if self.is_team else DraftMode.NO_TRADE
        if self.draft_mode in (DraftMode.NO_TRADE, DraftMode.WITH_TRADE):
            drafts = DraftModule.get_draft(len(self.members), '.'.join(str(i) for i in self.banned_leaders), client=client)
            await DraftModule.draw_draft(drafts, (m.mention for m in self.members), self.channel)
            return
        if self.draft_mode == DraftMode.RANDOM:
            await self.channel.send("Draft Mode selected is all random, the draft is finished (you can change random leader pool in game settings to apply bans).")
            return
        if self.draft_mode == DraftMode.CWC:
            await self.channel.send("Draft Mode selected is CWC, continue in the lobby with Multiplayer Helper.")
            return
        if self.draft_mode == DraftMode.BLIND:
            draft = BlindDraft(self.members, '.'.join(str(i) for i in self.banned_leaders))
            await draft.run(self.channel, client)
            return
        if self.draft_mode == DraftMode.DRAFT_2:
            drafts = DraftModule.get_draft(2,  '.'.join(str(i) for i in self.banned_leaders), client=client)
            await DraftModule.draw_draft(drafts, (f"Team {i}" for i in range(1, 3)), self.channel)
        if self.draft_mode == DraftMode.DDRAFT_9_3_1:
            # Fetching captains
            cap_1, cap_2 = await self.fetchs_captains(client)
            args = [None, '9', '.'.join(str(i) for i in self.banned_leaders), 'max', '3', '1']
            drafts_lines = DraftModule.get_draft(9, *args[2:4], client=client)
            ddraft = DynamicDraft(args, drafts_lines, cap_1, cap_2)
            await ddraft.run(self.channel, client)

    async def fetchs_captains(self, client) -> Tuple[nextcord.User, nextcord.User]:
        msg = await self.channel.send("Waiting for 2 captains ...")
        await msg.add_reaction(EMOJI_CROWN)
        captains : List[nextcord.User] = []
        while len(captains) < 2:
            try:
                _, user = await client.wait_for('reaction_add',
                                             timeout=300,
                                             check=lambda reaction, user_: user_ in self.members and reaction.message.id == msg.id)
                if user not in captains:
                    captains.append(user)
                    await msg.edit(content="Waiting for 2 captains ...\nCaptains: " + ' '.join(i.mention for i in captains))
            except asyncio.TimeoutError:
                raise Timeout("No captains reacted in 5 minutes, Timeout.")
        return tuple(captains)

    async def on_reaction_add(self, reaction, user, client) -> bool:
        if reaction.message.id not in self.msg_ids or user.id == client.user:
            if datetime.now(tz=timezone.utc) > self.delete_at:
                try:
                    await self.delete_draft()
                except Exception as e:
                    logger.error(f"{e.__class__.__name__}: {e}")
                    pass
                return True
            return False
        if user.id not in self.members_id:
            try:
                await reaction.remove(user)
                return False
            except nextcord.HTTPException:
                return False
        if reaction.message.id == self.confirm_msg.id and user.id in self.waiting_members:
            self.waiting_members.remove(user.id)
            await self.edit_confirm_msg(self.confirm_msg)
            if not self.waiting_members:
                asyncio.create_task(self.run_draft(client))
                return True
        if reaction.message.id == self.ban_msg.id:
            emoji: nextcord.Emoji = reaction.emoji
            if not isinstance(emoji, nextcord.Emoji):
                return False
            leader = leaders.get_leader_by_emoji_id(reaction.emoji.id)
            if not leader:
                return False
            if (await self.is_vote_winner(reaction)) and leader not in self.banned_leaders:
                self.banned_leaders.append(leader)
                await self.edit_ban_msg(self.ban_msg, client)
        elif reaction.message.id in self.votes_msg_ids and (await self.is_vote_winner(reaction)):
            winner = self.get_winner_by_emoji_str(str(reaction.emoji), self.msg_to_vote[reaction.message.id])
            if not winner:
                return False
            msg: nextcord.Message = reaction.message
            await asyncio.gather(msg.clear_reactions(),
                                 msg.edit(content="__**{0[0]}**__: {0[1]} {0[2]}".format(winner)))
            if winner[0] == DRAFT_MODE_TITLE:
                self.draft_mode = DraftMode(winner[2])
                if self.draft_mode == DraftMode.CWC:
                    await self.ban_msg.delete()
        return False

    async def delete_draft(self):
        await self.channel.delete_messages(self.sended)
        await self.ban_msg.delete()
        await self.confirm_msg.edit(content="**Vote delete due to inactivity**. Inactive peoples: " + ','.join(f"<@{i}>" for i in self.waiting_members))

    @classmethod
    def check_if_instance_is_busy(cls):
        print("busy: ", cls._instance_busy)
        if cls._instance_busy:
            raise BusyException("Another Vote is in creation, please wait ...")

    @staticmethod
    async def send_ban_msg(channel) -> nextcord.Message:
        msg = await channel.send("__**Civ Bans**__: Select civs to ban from emoji list.")
        await msg.add_reaction("🚫")
        return msg

    async def send_default_msg(self, setting, default, channel) -> nextcord.Message:
        msg = await channel.send(f"{setting}: {default}")
        return msg

    async def edit_ban_msg(self, msg, client):
        await msg.edit(content="__**Civ Bans**__: Select civs to ban from emoji list.\n" +
                       '\n'.join(f"{client.get_emoji(i.emoji_id)} {i.civ}" for i in self.banned_leaders))

    async def send_confirm_msg(self, channel) -> nextcord.Message:
        msg = await channel.send("Waiting for : " + ', '.join(f"<@{i}>" for i in self.waiting_members))
        await msg.add_reaction(EMOJI_PLUS)
        return msg

    async def edit_confirm_msg(self, msg):
        await msg.edit(content="Waiting for : " + ', '.join(f"<@{i}>" for i in self.waiting_members))

    async def is_vote_winner(self, reaction : nextcord.Reaction) -> bool:
        users = await reaction.users().flatten()
        ls = list(filter(lambda user: user.id in self.members_id, users))
        if len(ls) >= self.majority:
            return True
        return False

    @staticmethod
    async def send_line(name, line, channel):
        msg = await channel.send(f"__**{name}**__:  " + '  |  '.join(f"{i} {j}" for i, j in line))
        for reaction, _ in line:
            await msg.add_reaction(reaction)
        return msg

    def get_winner_by_emoji_str(self, reaction_str : EMOJI, vote : Tuple[str, Iterable[Tuple[EMOJI, str]]]) -> Optional[Tuple[str, EMOJI, str]]:
        for line in vote[1]:
            if line[0] == reaction_str:
                return (vote[0], *line)
        return None

class SecretVote:
    _instance_busy = False

    def __init__(self, votetype, civ, members, vote_settings, channel, message_string):
        self.civ = civ + ' ' + message_string
        self.members = members
        self.members_id = [i.id for i in members]
        self._vote_settings = vote_settings[votetype]
        self.vote_type = votetype
        self.channel = channel
        self.msg_ids = []
        self.sended = []
        self.votes = {}
        self.votes_msg_ids = []
        self.msg_to_vote = {}
        self.votes = {}
        self.majority = len(self.members) // 2 + 1
        self.waiting_members = self.members_id.copy()

        self.sent = None
        self.confirm_msg = None
        self.has_confirm = False
        self.question = None

        self.channel = channel
        self.created_at = datetime.now(tz=timezone.utc)
        self.delete_at = self.created_at + timedelta(minutes=MINUTES_BEFORE_REMOVING_VOTE)

    def __repr__(self):
        return f"<SecretVote members={self.members}, waiting_members={self.waiting_members}>"

    async def run(self, channel : nextcord.TextChannel):
        self.check_if_instance_is_busy()
        SecretVote._instance_busy = True
        try:
            for k, v in self._vote_settings.items():
                title = "Question: " + k + " "  +  self.civ + ":grey_question::grey_question:"
            em = nextcord.Embed(title=":detective: Secret vote :detective:", description=title)
            em.add_field(name=":alarm_clock:Players", value='\n'.join(i.mention for i in self.members))
            self.question = await self.channel.send(embed=em)

            self.sent = await asyncio.gather(*[self.send_line(k + " " + self.civ, v, member) for k, v in self._vote_settings.items() for member in self.members])
        except Exception as e:
            raise BotException from e
        finally:
            SecretVote._instance_busy = False

        self.votes_msg_ids = [i.id for i in self.sent]
        self.msg_ids = [*self.votes_msg_ids]
        self.msg_to_vote : Dict[int, Tuple[str, List[Tuple[EMOJI, str]]]] = {self.sent[i].id: (name, v) for i, (name, (v)) in enumerate(self._vote_settings.items())}

        timeout = time.time() + 120
        while time.time() < timeout and len(self.waiting_members) > 0:
            await asyncio.sleep(1)
        if len(self.waiting_members) > 0:
            await self.delete_vote()

    async def on_reaction_add(self, reaction, user, client) -> bool:
        if reaction.message.id not in self.msg_ids or user.id == client.user:
            return False
        if reaction.message.id in self.votes_msg_ids and user.id in self.waiting_members:
            self.waiting_members.remove(user.id)
            self.votes[str(reaction.emoji)] = self.votes.get(str(reaction.emoji), 0) + 1
            await self.finish_vote()
            if not self.waiting_members:
                return True
        return False

    @classmethod
    def check_if_instance_is_busy(cls):
        if cls._instance_busy:
            raise BusyException("Another Vote is in creation, please wait ...")

    @staticmethod
    async def send_line(name, line, member):
        description = f"**{name}**:  " + '  |  '.join(f"{i} {j}" for i, j in line)
        msg = await member.send(embed=nextcord.Embed(title="Secret vote", description=description))
        for reaction, _ in line:
            await msg.add_reaction(reaction)
        return msg

    def get_winner(self):
        winner = max(self.votes.items(), key=lambda x: x[1])
        return winner
    
    async def delete_vote(self):
        for i in self.sent:
            await i.delete()
        if len(self.waiting_members):
            await self.channel.send(f"The following members were inactive and have been automatically marked as 'yes' votes: {', '.join(f'<@{i}>' for i in self.waiting_members)}")
        self.votes[str(EMOJI_OK)] = self.votes.get(str(EMOJI_OK), 0) + len(self.waiting_members)
        self.waiting_members = None
        await self.finish_vote()

    async def finish_vote(self):
        for k, v in self._vote_settings.items():
            line = v
            title = "Question: " + k + " " + self.civ + ":grey_question::grey_question:"
        if self.waiting_members:
            awaiting = "\n\n:alarm_clock: Awaiting vote from:\n" + '\n'.join(f"<@{i}>" for i in self.waiting_members)
        else:
            awaiting = "\n\nVote finished :checkered_flag:"
        description = f"{title}{awaiting}"
        em = nextcord.Embed(title=":detective: Secret vote :detective:", description=description)
        if not self.waiting_members:
            for i, j in line:
                em.add_field(name=f"{i} {j}", value=f"{self.votes.get(str(i), 0)}")
        await self.question.edit(embed=em)