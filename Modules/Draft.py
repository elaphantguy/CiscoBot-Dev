import nextcord
import asyncio
import random
from enum import IntEnum
from typing import Iterable, List, Dict, Optional, Tuple

from .abcModule import abcModule

from Leaders import leaders, Leader
from exc import InvalidArgs,ALEDException, AntiRelouException
from utils import get_member_in_channel, get_member_by_name
from constant import NB

class DraftModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"draft": self.cmd_draft,
                         "blinddraft": self.cmd_blinddraft,
                         "ddraft": self.cmd_ddraft}
        self.events = {"on_message": [self.on_message]}

    async def on_message(self, message):
        if message.content.startswith(".draft-"):
            _, o = message.content.split('-', 1)
            nb, bans = o.split('.', 1)
            await message.channel.send(f"Deprecated command: please use this new syntax : ``.draft {nb} {bans}``")

    async def cmd_draft(self, *args : str, channel, member, **_):
        if not args:
            raise InvalidArgs("Command should take at least one parameter")
        if args[0].lower() == 'ffa':
            members = get_member_in_channel(member.voice)
            nb = len(members)
            generator = (m.mention for m in members)
        else:
            if not args[0].isdigit():
                raise InvalidArgs("1st Argument must be a integer (exemple: ``.draft 2``) or 'FFA'")
            nb = int(args[0])
            if nb > 100:
                raise AntiRelouException("Atempting to run a draft with more than 100 lines")
            generator = (f"n°{i+1}" for i in range(nb))
        drafts = self.get_draft(nb, *args[1:], client=self.client)
        await self.draw_draft(drafts, generator, channel)

    async def cmd_ddraft(self, *args: str, channel, client, member, guild, **_):
        """/ddraft {nb} {bans} {leader_per_draft} {pick_per_team} {ban_per_team} {timer}"""
        if not args:
            raise InvalidArgs("Command should take at least two parameter")
        if not args[1].isdigit():
            raise InvalidArgs("2nd Argument must be a integer (exemple: ``/ddraft @iElden 8``)")
        nb = int(args[1])
        drafts_lines = self.get_draft(nb, *args[2:4], client=client)
        draft = DynamicDraft(args, drafts_lines, member, get_member_by_name(args[0], guild))
        await draft.run(channel, client)



    async def cmd_blinddraft(self, *args : str, channel, member, **_):
        bd = BlindDraft(get_member_in_channel(member.voice), *args)
        await bd.run(channel, client=self.client)

    @staticmethod
    async def draw_draft(drafts, generator, channel):
        for i, g in enumerate(generator):
            await channel.send("**Player {}**\n{}".format(g, drafts[i].replace(',', '\n')))

    @classmethod
    def get_raw_draft(cls, nb: int, *args) -> Iterable[List[Leader]]:
        pool = leaders.leaders[:]
        if len(args) >= 1:
            ban_query = args[0].split('.')
            for ban in ban_query:
                if not ban:
                    continue
                lead = leaders.get_leader_named(ban)
                if not lead:
                    raise InvalidArgs(f"Leader \"{ban}\" not found")
                if lead in pool:
                    pool.remove(lead)
        leader_per_player = len(pool) // nb
        if len(args) >= 2:
            if args[1] != 'max':
                if not args[1].isdigit():
                    raise InvalidArgs(
                        "3rd Argument (max civ per draft) must be a integer or \"max\" (exemple: ``.draft 8 Maori.Colombie 4``)")
                leader_per_player = int(args[1])
        random.shuffle(pool)
        return (pool[i * leader_per_player:i * leader_per_player + leader_per_player] for i in range(nb))

    @classmethod
    def get_draft(cls, nb: int, *args, client) -> List[str]:
        pools = cls.get_raw_draft(nb, *args)
        return [','.join(f"{client.get_emoji(j.emoji_id)} {j}" for j in sorted(pool)) for pool in pools]

class BlindDraft:
    def __init__(self, members, *args):
        self.members = members
        self.pools = [i[:20] for i in DraftModule.get_raw_draft(len(members), *args)]
        self.pool_per_member = {k.id: v for k, v in zip(self.members, self.pools)}  # type: Dict[int, List[Leader]]
        self.picks = {k.id: None for k in self.members}  # type: Dict[int, Optional[Leader]]

    async def run(self, channel : nextcord.TextChannel, client):
        msg = await channel.send(embed=nextcord.Embed(title="Blind draft", description="Sending draft in PM !"))
        tasks = (self.send_bdrafts(member, pool, client=client) for member, pool in zip(self.members, self.pools))
        mps = await asyncio.gather(*tasks)
        mp_per_member = {k.id: v for k, v in zip(self.members, mps)}

        def check(reac_ : nextcord.Reaction, user_ : nextcord.User):
            return (user_.id in mp_per_member.keys() and
                    reac_.message.id in (i.id for i in mp_per_member.values()))

        await msg.edit(embed=self.get_embed(client=client))
        while True:
            reaction, user = await client.wait_for('reaction_add', check=check)
            leader = leaders.get_leader_by_emoji_id(reaction.emoji.id)
            if leaders.get_leader_by_emoji_id(reaction.emoji.id) not in self.pool_per_member[user.id]:
                continue
            self.picks[user.id] = leader
            await msg.edit(embed=self.get_embed(client=client))
            if self.is_finished:
                return

    @staticmethod
    async def send_bdrafts(member, pool, *, client):
        em = nextcord.Embed(title="Blind Draft",
                           description='\n'.join(f"{client.get_emoji(i.emoji_id)} {i.civ}" for i in pool))
        em.add_field(name="Status", value="Click on a reaction to select your leader\n(you may not choose a civ you do not own and you may not trade or change your chosen civ under any circumstances)")
        msg = await member.send(embed=em)
        tasks = (msg.add_reaction(client.get_emoji(i.emoji_id)) for i in pool)
        await asyncio.gather(*tasks)
        return msg

    @staticmethod
    async def edit_bdrafts(message, pool, *, client):
        em = nextcord.Embed(title="Blind Draft",
                           description='\n'.join(f"{client.get_emoji(i.emoji_id)} {i.civ}" for i in pool))
        em.add_field(name="Status", value="You have chose your Leader !")
        await message.edit(embed=em)

    def get_embed(self, *, client):
        em = nextcord.Embed(title="Blind Draft")
        em.add_field(name="Players", value='\n'.join(f"<@{i}>" for i in self.picks.keys()))
        if self.is_finished:
            em.add_field(name="Picks",
                         value='\n'.join(f"{client.get_emoji(i.emoji_id)} {i.civ}" for i in self.picks.values()))
        else:
            em.add_field(name="Picks",
                         value='\n'.join(("Waiting ..." if i is None else "Picked") for i in self.picks.values()))
        return em

    @property
    def is_finished(self):
        return None not in self.picks.values()

class DynamicDraft:
    ICONS = ['?', '🚫', chr(0x1f7eb), chr(0x1f7e6)]
    class DraftLineState(IntEnum):
        NONE = 0
        BANNED = 1
        PICKED_1 = 2
        PICKED_2 = 3

        @classmethod
        def get_icon(cls, draftLineState, nb) -> str:
            if draftLineState is not cls.NONE:
                return DynamicDraft.ICONS[draftLineState.value]
            return NB[nb]

    class DraftLine:
        def __init__(self, draft_line):
            self.state = DynamicDraft.DraftLineState.NONE
            self.line = draft_line

    class ActionType(IntEnum):
        BAN = 0
        PICK = 1

    def __init__(self, args, drafts_lines, cap1, cap2):
        self.ban_per_team, self.pick_per_team, self.base_timer = self._parse_args(args, len(drafts_lines))
        self.timer = self.base_timer * 2
        self.ban_phase = [1, 2] * self.ban_per_team
        self.pick_phase = [1, 2] + [2, 1, 1, 2] * ((self.pick_per_team - 1) // 2) + ([] if self.pick_per_team % 2 else [2, 1])
        self.caps = (cap1, cap2)  # type: Tuple[nextcord.Member, nextcord.Member]

        self.phase = self.ActionType.BAN  # type: DynamicDraft.ActionType
        self.phase_nb = -1  # type: int
        self.is_ended = False
        self._next_phase()

        self.drafts = [self.DraftLine(draft_line) for draft_line in drafts_lines]  # type: List[DynamicDraft.DraftLine]

    async def run(self, channel, client):
        msg = await channel.send(embed=self.to_embed())
        for i, _ in enumerate(self.drafts):
            await msg.add_reaction(NB[i])

        while True:
            try:
                reaction, _ = await client.wait_for('reaction_add', timeout=3, check=lambda reac,
                                                                                            user: user == self.get_member_needed_for_action() and reac.message.id == msg.id)
            except asyncio.TimeoutError:
                if self.timer > -5:
                    self.update_timer(3)
                    asyncio.create_task(msg.edit(embed=self.to_embed()))
                else:
                    self.reset_timer()
                    rt = self.update(None)
                    await msg.edit(embed=self.to_embed())
                    if rt:
                        return
                continue
            try:
                n = NB.index(str(reaction))
            except ValueError:
                continue
            self.reset_timer()
            rt = self.update(n)
            await msg.edit(embed=self.to_embed())
            if rt:
                return

    @staticmethod
    def _parse_args(args, draft_len):
        ban_per_team = 0
        if len(args) >= 6:
            if not args[5].isdigit():
                raise InvalidArgs(f"Number of ban per team must be a int, not \"{args[5]}\"")
            ban_per_team = int(args[5])
        pick_per_team = (draft_len - ban_per_team * 2) // 2
        if len(args) >= 5:
            if args[4] != "max":
                if not args[4].isdigit():
                    raise InvalidArgs(f"Number of pick per team must be a int or \"max\", not \"{args[4]}\"")
                pick_per_team = int(args[4])
                if pick_per_team > (draft_len - ban_per_team * 2) // 2:
                    raise InvalidArgs(f"There is not enough draft for this number of ban/pick per team")
        timer = 60
        if len(args) >= 7:
            if not args[6].isdigit():
                raise InvalidArgs(f"Timer must be a int, not \"{args[6]}\"")
            timer = int(args[6])
        return ban_per_team, pick_per_team, timer

    def to_embed(self):
        descs : List[str] = []
        txt = ""
        for i in self._get_draft():
            if len(txt) + len(i) >= 2000:
                descs.append(txt)
                txt = i
            else:
                txt += '\n' + i
        descs.append(txt)

        em = nextcord.Embed(title="Dynamic Draft", description=descs[0])
        if len(descs) > 1:
            em.add_field(name="\u200b", value=descs[1], inline=False)
        if self.is_ended:
            em.add_field(name="Progress",
                         value=f"Draft finished\n{self.ICONS[2]} {self.caps[0].mention}'s Team\n{self.ICONS[3]} {self.caps[1].mention}'s Team",
                         inline=False)
        else:
            em.add_field(name="Progress",
                         value=f"```ml\n{self._get_phase()}``````md\n{self._get_phase_tl()}```\n{self._get_action_needed()} **({max(self.timer, 0)}s)**",
                         inline=False)
        return em

    def get_current_phase(self):
        return self.ban_phase if self.phase == self.ActionType.BAN else self.pick_phase

    def _get_draft(self) -> List[str]:
        result = []
        for i, draft in enumerate(self.drafts):
            result.append(f"{self.DraftLineState.get_icon(draft.state, i)} {draft.line}")
        return result

    def _get_phase(self) -> str:
        if self.phase == self.ActionType.BAN:
            return f"<Ban> pick"
        return f"ban <Pick>"

    def _get_phase_tl(self) -> str:
        phase = self.get_current_phase()
        if not phase:
            return "..."
        return (' '.join(str(i) for i in phase[:self.phase_nb]) + '<' + str(phase[self.phase_nb])
            + '>' + ' '.join(str(i) for i in phase[self.phase_nb+1:]))

    def _get_action_needed(self):
        return f"{self.ICONS[self.get_team_needed_for_action() + 1]} {self.get_member_needed_for_action().mention} must choose a draft to {'ban' if self.phase == self.ActionType.BAN else 'pick'}"

    def get_team_needed_for_action(self) -> int:
        return self.get_current_phase()[self.phase_nb]

    def get_member_needed_for_action(self) -> nextcord.Member:
        return self.caps[self.get_team_needed_for_action() - 1]

    def update(self, n) -> bool:  # return true if finished
        if n is None:  # player timeout
            return self._next_phase()
        if n > len(self.drafts):
            return False
        if self.drafts[n].state != self.DraftLineState.NONE:
            return False
        team_needed = self.get_team_needed_for_action()
        if self.phase == self.ActionType.BAN:
            self.drafts[n].state = self.DraftLineState.BANNED
        elif team_needed == 1:
            self.drafts[n].state = self.DraftLineState.PICKED_1
        elif team_needed == 2:
            self.drafts[n].state = self.DraftLineState.PICKED_2
        else:
            raise ALEDException(f"DynamicDraft.update() got {n} as n parameter")
        return self._next_phase()

    def _next_phase(self) -> bool:
        self.phase_nb += 1
        if self.phase_nb >= len(self.get_current_phase()):
            if self.phase == self.ActionType.BAN:
                self.phase = self.ActionType.PICK
                self.phase_nb = 0
            else:
                self.is_ended = True
                return True
        return False

    def update_timer(self, n):
        self.timer -= n

    def reset_timer(self):
        self.timer = self.base_timer * ((self.phase_nb <= 1 and self.phase == self.ActionType.BAN) + 1)