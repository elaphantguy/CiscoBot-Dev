import nextcord
import asyncio
from typing import List, Tuple, Callable, Dict
from datetime import datetime, timedelta, timezone
from trueskill import TrueSkill, Rating
import logging

from .abcModule import abcModule
from models.DbModel import PlayerStats2
from models.ReportParser import GameType
from models.ReportParser import Match
from Database import Database
from utils import get_member_by_name, get_member_in_channel, admin_command, moderator_command
from config import MU, SIGMA, BETA, TAU, SKILL, QUITTER_MAX_POINT, SUBBED_MAX_POINT, SUB_MINIMUM_POINT, DONT_CHANGE_SIGMA_ON_PENALTIES,\
    RANKS_ROLES, CPL_GUILD_ID, RANKED_ROLE, LEADERBOARDS, SEASON_LEADERBOARDS
from exc import NotFound, ALEDException

GET_SORTING_RANK : Callable[[PlayerStats2], int] = lambda playerStat: 0 if not playerStat.games else int(playerStat.skill)
GET_STAT : Callable[[int], str] = lambda i: '   -' if i == 0 else f"{i:>4}"

logger = logging.getLogger("RankedModule")

class RankedModule(abcModule):
    def __init__(self, client):
        super().__init__(client)
        self.commands = {"stats": self.cmd_stats,
                         "oldstats": self.cmd_legacy_stats,
                         "roomranking": self.cmd_roomranking,
                         "updateleaderboards": self.cmd_updateleaderboards,
                         "recalcallrank": self.cmd_recalcallrank}
        self.events = {"on_validate_match": [self.on_validate_match]}

        self.next_leaderboard_update : Dict[str, datetime] = {}

        self.ranks_roles : List[Tuple[str, nextcord.Role, int]]=\
            [(i, client.get_guild(CPL_GUILD_ID).get_role(j), k) for i, j, k in RANKS_ROLES]
        self.rankPreviewer = RankPreviewer(self.database, self)
        self.env = TrueSkill(mu=MU, sigma=SIGMA, beta=BETA, tau=TAU, draw_probability=0.01)

    async def on_validate_match(self, match):
        print("ON_VALID_MATCH")
        await self.update_player_rank(match)
        await self.update_leaderboard_request(match.gametype)

    async def update_player_rank(self, match : Match):
        old_ranks = self.rankPreviewer.get_current_rank_for_players(match)
        new_ranks = self.rankPreviewer.calc_new_ranks(match, old_ranks)
        for player, old_rank, rank in zip(match.players, old_ranks, new_ranks):
            for table in ['stats2', 'current_season']:
                stat = self.database.get_playerstats_by_id(gameType=match.gametype.value, discord_id=player.id, table=table)
                Rating.__init__(stat, rank.mu, rank.sigma)
                # Update player stats
                stat.games += 1
                stat.wins += SKILL(rank) >= SKILL(old_rank)
                stat.first += player.position == 1
                stat.subbedIn += 'SUB' in player.flags
                stat.subbedOut += 'SUBBED' in player.flags
                stat.civs[player.leader.uuname] = stat.civs.get(player.leader.uuname, 0) + 1
                self.database.set_playerstats(stat, table=table)
                await asyncio.create_task(self.recalc_rank_role_by_id(player.id))

    async def update_leaderboard(self, gametype : GameType):
        players = self.database.get_all_playerstats(gametype.value)
        cfg = LEADERBOARDS.get(gametype.value)
        if not cfg:
            raise ALEDException(f"Can't find Leaderboard configuration for GameType \"{gametype.value}\"")
        channel = self.client.get_channel(cfg['channel_id'])
        if not channel:
            raise ALEDException(f"Can't find channel ID {cfg['channel_id']} for following Leaderboard : \"{gametype.value}\"")
        players.sort(key=lambda pl_: pl_.skill, reverse=True)
        txt = "`Rank  Skill  [wins - loss]  win%  1st`\n"
        for j, msg_id in enumerate(cfg['message_id']):
            msg : nextcord.PartialMessage = channel.get_partial_message(msg_id)
            for i in range(j*10, (j+1)*10):
                if i >= len(players):
                    txt += f"`#{i+1:<3}      -  [     -     ]     -    -`\n"
                else:
                    pl = players[i]
                    txt += f"`#{i+1:<3}  {int(pl.skill):>5}  [ {pl.wins:>3} - {pl.games-pl.wins:<3} ]  {pl.wins/pl.games:4.0%}  {pl.first:>3}` <@{pl.id}>\n"
            await msg.edit(content=txt)
            txt = ""
        await self.update_season_leaderboard(gametype)

    async def update_season_leaderboard(self, gametype : GameType):
        players = self.database.get_all_season_playerstats(gametype.value)
        print (f', '.join(f'{p}' for p in players))
        cfg = SEASON_LEADERBOARDS.get(gametype.value)
        if not cfg:
            raise ALEDException(f"Can't find Leaderboard configuration for GameType \"{gametype.value}\"")
            print(f"Can't find Leaderboard configuration for GameType \"{gametype.value}\"")
        channel = self.client.get_channel(cfg['channel_id'])
        if not channel:
            raise ALEDException(f"Can't find channel ID {cfg['channel_id']} for following Leaderboard : \"{gametype.value}\"")
        players.sort(key=lambda pl_: pl_.skill, reverse=True)
        txt = "`Rank  Skill  [wins - loss]  win%  1st`\n"
        for j, msg_id in enumerate(cfg['message_id']):
            msg : nextcord.PartialMessage = channel.get_partial_message(msg_id)
            for i in range(j*10, (j+1)*10):
                if i >= len(players):
                    txt += f"`#{i+1:<3}      -  [     -     ]     -    -`\n"
                else:
                    pl = players[i]
                    txt += f"`#{i+1:<3}  {int(pl.skill):>5}  [ {pl.wins:>3} - {pl.games-pl.wins:<3} ]  {pl.wins/pl.games:4.0%}  {pl.first:>3}` <@{pl.id}>\n"
            await msg.edit(content=txt)
            txt = ""

    async def update_leaderboard_request(self, gametype : GameType):
        next_updated = self.next_leaderboard_update.get(gametype.value, None)
        if next_updated is not None and datetime.now(tz=timezone.utc) < next_updated:
            return
        self.next_leaderboard_update[gametype.value] = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        await self.update_leaderboard(gametype)

    async def update_leaderboards(self):
        #for gametype in GameType:
        await self.update_leaderboard(GameType.FFA)

    async def cmd_stats(self, *args, channel, member, guild, **_):
        if args:
            target_name = ' '.join(args)
            target = get_member_by_name(target_name, guild or self.client)
            if not target:
                raise NotFound(f"Member \"{target_name}\" not found")
        else:
            target = member

        playerStatsFFA = self.database.get_playerstats_by_id('FFA', target.id)
        em = playerStatsFFA.to_embed(target)
        playerStatsTeamer = self.database.get_playerstats_by_id('Teamer', target.id)
        if playerStatsTeamer.games:
            playerStatsTeamer.create_embed_field(em)
        playerStatsPBC = self.database.get_playerstats_by_id('PBC', target.id)
        if playerStatsPBC.games:
            playerStatsPBC.create_embed_field(em)
        await channel.send(embed=em)

    async def cmd_legacy_stats(self, *args, channel, member, guild, **_):
        if args:
            target_name = ' '.join(args)
            target = get_member_by_name(target_name, guild or self.client)
            if not target:
                raise NotFound(f"Member \"{target_name}\" not found")
        else:
            target = member

        playerStats = self.database.get_legacy_playerstats_by_id('ffa', target.id)
        await channel.send(embed=playerStats.to_embed(target))

    async def cmd_roomranking(self, *args, channel : nextcord.TextChannel, member : nextcord.Member, **_):
        members = get_member_in_channel(member.voice)
        stats : List[Tuple[nextcord.Member, Tuple[int, ...]]] =[
            (member, tuple([GET_SORTING_RANK(self.database.get_playerstats_by_id(gametype.value, member.id))
             for gametype in GameType])) for member in members]
        stats.sort(key=lambda x: x[1], reverse=True)
        ml = max(len(i.display_name) for i in members)
        header = f"```py\n{'Name':<{ml}}| {' | '.join(f'{gt.value[:4]:>4}' for gt in GameType)}\n"
        txt = '\n'.join(f"{member.display_name:<{ml}}: "+ ' | '.join(GET_STAT(i) for i in stat) for member, stat in stats)
        await channel.send(header + txt + '```\n')

    @moderator_command
    async def cmd_updateleaderboards(self, *args, channel, **_):
        await self.update_leaderboards()
        await channel.send("done")

    def get_role_for_elo(self, elo : float) -> nextcord.Role:
        role = None
        for _, role, threshold in self.ranks_roles:
            if elo >= threshold:
                return role
        return role

    async def recalc_rank_role(self, member):
        if member is None:
            logger.warning(f"Member {member} not found for recalc role")
            return
        playerStat = self.database.get_playerstats_by_id('FFA', member.id)
        role = self.get_role_for_elo(playerStat.skill)
        if role in member.roles:
            return
        await member.remove_roles(*(role for name, role, elo in self.ranks_roles))
        if RANKED_ROLE in [i.id for i in member.roles]:
            await member.add_roles(role)

    async def recalc_rank_role_by_id(self, discord_id):
        cpl = self.client.get_guild(CPL_GUILD_ID)
        member = cpl.get_member(discord_id)
        await self.recalc_rank_role(member)

    @admin_command
    async def cmd_recalcallrank(self, *args, channel : nextcord.TextChannel, guild : nextcord.Guild, **_):
        total_member = len(guild.members)
        for i, member in enumerate(guild.members):
            try:
                if i % 100 == 0:
                    await asyncio.create_task(channel.send(f"Processed {i}/{total_member}"))
                pl_roles = [i.id for i in member.roles]
                if RANKED_ROLE in pl_roles and 628464491129995264 in pl_roles:
                    continue
                print(f"calc for {i}: {member}")
                await asyncio.create_task(self.recalc_rank_role(member))
            except Exception as e:
                print(f"{type(e).__name__}: {e}")
        await channel.send("Done")

class RankPreviewer:
    from typing import List, Iterable
    from models.ReportParser import Report

    def __init__(self, database, ranked_module):
        self.database = database
        self.ranked_module = ranked_module

    def get_current_rank_for_players(self, report : Report) -> List[Rating]:
        return [self.database.get_playerstats_by_id(report.gametype.value, pl.id).get_rating() for pl in
                report.players]

    def calc_new_ranks(self, report : Report, old_ranks : List[Rating], apply_penalties=True) -> List[Rating]:
        try:
#            if report.gametype == GameType.TEAMER:
#                print("teamer", [tuple([old_ranks[i] for i, pl in enumerate(report.players) if pl.position == pos and not report.player_is_subbed(pl)])
#                                                 for pos in range(1, max([pl.position for pl in report.players])+1)])
#                new_ranks = self.to_1d(
#                    self.ranked_module.env.rate([tuple([old_ranks[i] for i, pl in enumerate(report.players) if pl.position == pos and not report.player_is_subbed(pl)])
#                                                 for pos in range(1, max([pl.position for pl in report.players])+1)])
#                )
#            else:
#                print("ffa", [(i,) for i in old_ranks], [pl.position for pl in report.players])
            new_ranks = self.to_1d(
                self.ranked_module.env.rate([(i,) for i in old_ranks], ranks=[pl.position for pl in report.players])
            )
        except ValueError as e:
            logger.error(f"{type(e).__name__}: {e}")
            return old_ranks
        if apply_penalties:
            for i, pl in enumerate(report.players):
                if Match.player_is_subbed(pl):
                    new_ranks[i] = Rating(mu=min(old_ranks[i].mu + SUBBED_MAX_POINT, new_ranks[i].mu),
                                          sigma=old_ranks[i].sigma if DONT_CHANGE_SIGMA_ON_PENALTIES else new_ranks[i].sigma)
                if Match.player_is_sub(pl):
                    new_ranks[i] = Rating(mu=max(old_ranks[i].mu + SUB_MINIMUM_POINT, new_ranks[i].mu),
                                          sigma=old_ranks[i].sigma if DONT_CHANGE_SIGMA_ON_PENALTIES else new_ranks[i].sigma)
                if Match.player_is_quitter(pl):
                    new_ranks[i] = Rating(mu=min(old_ranks[i].mu + QUITTER_MAX_POINT, new_ranks[i].mu),
                                          sigma=old_ranks[i].sigma if DONT_CHANGE_SIGMA_ON_PENALTIES else new_ranks[i].sigma)
        return new_ranks

    def get_ranks_preview(self, report : Report) -> List[float]:
        old_ranks = self.get_current_rank_for_players(report)
        new_ranks = self.calc_new_ranks(report, old_ranks)
        is_teamer = report.gametype == GameType.TEAMER
        return [SKILL(new, teamer=is_teamer) - SKILL(old, teamer=is_teamer) for new, old in zip(new_ranks, old_ranks)]

    @staticmethod
    def to_1d(ls : List[Iterable]) -> List:
        return sum((list(i) for i in ls), [])
