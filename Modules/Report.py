import nextcord
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import utils
from .abcModule import abcModule
from .Ranked import RankedModule
from models.ReportParser import Match
from views.HistoryView import HistoryView
from views.BestCivView import BestCivView
from exc import NotFound, InvalidArgs

from config import REPORT_CHANNEL_ID, HISTORY_CHANNEL_ID
from constant import EMOJI_OK, EMOJI_NO, EMOJI_SCROLL
from utils import moderator_command, is_moderator

class ReportModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"validreport": self.cmd_validreport,
                         "reparsereport": self.cmd_reparsereport,
                         "reportsubs": self.cmd_reportsubs,
                         "history": self.cmd_history,
                         "bestcivs": self.cmd_bestcivs}
        self.events = {"on_message": [self.on_message], "on_edit": [self.on_edit], "on_delete": [self.on_delete],
                       "on_reaction_add": [self.on_reaction_change], "on_reaction_remove": [self.on_reaction_change]}

        self.report_channel = client.get_channel(REPORT_CHANNEL_ID)
        self.history_channel = client.get_channel(HISTORY_CHANNEL_ID)
        self._collapse_memory = {}
        self.rankPreviewer = None
        ranked_module = client.get_module(RankedModule)
        if ranked_module:
            self.rankPreviewer = ranked_module.rankPreviewer

    async def on_message(self, message):
        if message.channel.id != REPORT_CHANNEL_ID:
            return
        if not message.content.lower().startswith("game"):
            return
        match = Match.from_message(message)
        validation_msg = await message.channel.send(embed=match.to_embed())
        match.validation_msg_id = validation_msg.id
        self.database.add_match(match)
        await validation_msg.add_reaction(EMOJI_OK)
        await validation_msg.add_reaction(EMOJI_NO)
        await validation_msg.add_reaction(EMOJI_SCROLL)

    async def on_edit(self, payload : nextcord.RawMessageUpdateEvent):
        if payload.channel_id != REPORT_CHANNEL_ID:
            return
        match = self.database.get_match(payload.message_id)
        if match.report_id != payload.message_id:
            return
        message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        new_match = Match.from_message(message, validation_msg_id=match.validation_msg_id)
        self.database.edit_match(match.report_id, new_match)
        validation_msg = await self.client.get_channel(payload.channel_id).fetch_message(match.validation_msg_id)
        await self.update_embed(validation_msg, new_match, False)

    async def update_embed(self, message : nextcord.Message, match : Match, collapse : bool):
            await message.edit(embed=match.to_embed(collapsed=collapse,
                                                    contest_list=await self._get_contest_list(message),
                                                    rankPreviewer=self.rankPreviewer))
            await self.collapse_message_in(message)


    async def on_delete(self, payload : nextcord.RawMessageDeleteEvent):
        if payload.channel_id != REPORT_CHANNEL_ID:
            return
        match = self.database.get_match(payload.message_id)
        if not match:
            return
        validation_msg = await self.client.get_channel(payload.channel_id).fetch_message(match.validation_msg_id)
        await validation_msg.delete()
        # db.remove_match(match)

    async def on_reaction_change(self, payload : nextcord.RawReactionActionEvent):
        if payload.user_id == self.client.user.id:
            return
        if payload.channel_id != REPORT_CHANNEL_ID:
            return
        if str(payload.emoji) == EMOJI_OK:
            await self.on_reaction_validation(payload)
        if str(payload.emoji) == EMOJI_NO:
            await self.update_embed(await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id),
                                    self.database.get_match(payload.message_id),
                                    payload.message_id in self._collapse_memory.items())
        if str(payload.emoji) == EMOJI_SCROLL:
            message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await self.update_embed(message, self.database.get_match(payload.message_id), False)
            await self.collapse_message_in(message)

    async def on_reaction_validation(self, payload : nextcord.RawReactionActionEvent):
        member : nextcord.Member = self.client.get_guild(payload.guild_id).get_member(payload.user_id)
        if not is_moderator(member, self.client):
            return
        # Verify if report is more than 24h old
        if nextcord.utils.snowflake_time(payload.message_id) + timedelta(hours=24) > datetime.now(tz=timezone.utc):
            await member.send(f"The report is less than 24 hours old.\nUse `.validreport {payload.message_id}` to force the validation")
            return
        match = self.database.get_match(payload.message_id)
        if not match:
            raise NotFound(f"Can't find a match for ID {payload.message_id}")
        report_channel : nextcord.TextChannel = self.client.get_channel(payload.channel_id)
        validation_msg = await report_channel.fetch_message(payload.message_id)
        contestants = [i.id for i in await self._get_contest_list(validation_msg) if i.id in [p.id for p in match.players]]
        if contestants:
            contest_str = ' '.join(f"<@{i}>" for i in contestants)
            await member.send(f"The report is contested by {contest_str}.\nUse `.validreport {payload.message_id}` to force the validation")
            return
        await self.valid_report(match)

    async def valid_report(self, match : Match):
        report_msg = await self.report_channel.fetch_message(match.report_id)
        validation_msg = await self.report_channel.fetch_message(match.validation_msg_id)

        self.database.valid_match(match.report_id)
        await self.history_channel.send(match.to_history_message(self.rankPreviewer))
        await report_msg.delete()
        await validation_msg.delete()
        await self.client.on_validate_match(match)

    @moderator_command
    async def cmd_reparsereport(self, *args, **_):
        if not args:
            raise InvalidArgs("This command require argument (report ID)")
        if not args[0].isdigit():
            raise InvalidArgs(f"The 1st argument must be a int, not \"{args[0]}\"")
        match = self.database.get_match(int(args[0]))
        if not match:
            raise NotFound(f"Can't find a match for ID {args[0]}")
        await self.on_edit(nextcord.RawMessageUpdateEvent({'id': match.report_id, 'channel_id': self.report_channel.id}))

    @moderator_command
    async def cmd_validreport(self, *args, **_):
        if not args:
            raise InvalidArgs("This command require argument (report ID)")
        if not args[0].isdigit():
            raise InvalidArgs(f"The 1st argument must be a int, not \"{args[0]}\"")
        match = self.database.get_match(int(args[0]))
        if not match:
            raise NotFound(f"Can't find a match for ID {args[0]}")
        await self.valid_report(match)

    @moderator_command
    async def cmd_reportsubs(self, *args, channel, **_):
        dic : Dict[int, List[int]] = {}
        matchs = self.database.get_match_history_from(datetime.now(tz=timezone.utc) - timedelta(days=35))
        await channel.send(f"Scanning {len(matchs)} matchs ...", delete_after=10)
        for match in matchs:
            for pl in match.players:
                if 'SUBBED' in pl.flags:
                    if pl.id not in dic:
                        dic[pl.id] = []
                    dic[pl.id].append(match.report_id)
        ls = [f"[**{len(v)}**] <@{k}> (ID: {k}):\n" + '\n'.join(f"Match {i} @ {str(nextcord.utils.snowflake_time(i))}" for i in v)
              for k, v in dic.items() if len(v) >= 2]
        if not ls:
            await channel.send("No player have been subbed more than 2 times in the previous 35 days")
            return
        await channel.send("In the last 35 days:\n\n" + '\n\n'.join(ls))

    async def cmd_history(self, *args, channel, member, guild, **_):
        if not args:
            target = member
        else:
            target = utils.get_member_by_name(' '.join(args), guild or self.client)
        msg = await channel.send(embed=nextcord.Embed(title="Loading History ..."))
        history = self.database.get_match_history_for_player(target.id)
        view = HistoryView(member, target, history, msg, self.client)
        await msg.edit(**view.get_embed_and_view())

    async def cmd_bestcivs(self, *args, channel, member, guild, **_):
        if not args:
            target = member
        else:
            target = utils.get_member_by_name(' '.join(args), guild or self.client)
        msg = await channel.send(embed=nextcord.Embed(title="Loading History ..."))
        history = self.database.get_match_history_for_player(target.id)
        civ_history = self.get_civ_history(history, target.id)
        view = BestCivView(member, target, civ_history, msg, self.client)
        await msg.edit(**view.get_embed_and_view())

    async def collapse_message_in(self, message, seconds=30):
        self._collapse_memory[message.id] = datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)
        await asyncio.sleep(seconds+1)
        if datetime.now(tz=timezone.utc) > self._collapse_memory[message.id]:
            await self.update_embed(message, self.database.get_match(message.id), True)
            del self._collapse_memory[message.id]

    async def collapse_message(self, message_id):
        match = self.database.get_match(message_id)
        message = await self.report_channel.fetch_message(message_id)
        new_match = Match.from_str(message.content)
        validation_msg = await self.report_channel.fetch_message(match.validation_msg_id)
        await validation_msg.edit(embed=new_match.to_embed(collapsed=True,
                                                           contest_list=await self._get_contest_list(message),
                                                           rankPreviewer=self.rankPreviewer
        ))

    @staticmethod
    async def _get_contest_list(message : nextcord.Message):
        ls = [(await i.users().flatten()) for i in message.reactions if str(i) == EMOJI_NO]
        return ls[0] if ls else []

    @staticmethod
    def get_civ_history(history : List[Match], player_id):
        dic = {}
        for match in history:
            pl = match.get_player_by_id(player_id)
            uuname = pl.leader.uuname if pl.leader else 'unknown'
            d = dic.get(uuname, {'win': 0, 'lose':0, '1st': 0})
            if pl.position == 1:
                d['1st'] += 1
            if match.player_has_win(pl):
                d['win'] += 1
            else:
                d['lose'] += 1
            dic[uuname] = d
        return dict(sorted(dic.items(), key=lambda item: (item[1]['win'], -item[1]['lose']), reverse=True))