import nextcord
from enum import Enum, IntEnum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import re

from Leaders import Leader, leaders
from config import MODERATOR_TAG, AMBIGOUS_QUERY
from constant import EMOJI_SPY

POS_TO_STR = ["NULL", "1st", "2nd", "3rd"]
def pos_to_str(pos : int) -> str:
    if pos >= len(POS_TO_STR):
        return f"{pos}th"
    return POS_TO_STR[pos]

class Color(IntEnum):
    BLUE = 0x3498DB
    GREEN = 0x2ECC71
    YELLOW = 0xF1C40F
    RED = 0xE74C3C
    PURPLE = 0x9B59B6

class GameType(Enum):
    FFA = "FFA"
    TEAMER = "Teamer"
    PBC = "PBC"

GAMETYPE_ALIAS = {
    "duel": GameType.FFA,
    "cloud": GameType.PBC
}

MENTION = re.compile(r"<@!?(\d+)>\s*([^<]*)")
MENTION_SUB = re.compile(r"<@!?(\d+)>[^<]*SUB\s*(?:FOR)?\s*<@!?(\d+)>", flags=re.IGNORECASE)
VALID_FLAGS = ["QUITTER", "SUBBED", "SUB", "HOST"]

@dataclass
class GPlayer:
    id : int
    leader : Leader
    position : int
    flags : List[str]
    leader_query : Optional[str]

    def __repr__(self):
        return f"<GPlayer id: {self.id}, position: {self.position}, leader: {self.leader}>"

    def is_valid(self) -> bool:
        return bool(self.id and self.leader)

    def to_json(self):
        return {"id": self.id, "leader": self.leader and self.leader.uuname, "position": self.position, "flags": self.flags}

    @classmethod
    def from_json(cls, js):
        return cls(js['id'], leaders.get_leader(js['leader']), js['position'], js['flags'], None)

    def get_ambigous_civ(self) -> Optional[str]:
        if not self.leader_query:
            return None
        choice = AMBIGOUS_QUERY.get(self.leader_query.strip().lower(), None)
        if choice:
            return f"\"{self.leader_query}\" is ambigous, please use one of the following: {', '.join(choice)}"
        return None

class Report:
    def __init__(self, gametype, players):
        self.gametype : GameType = gametype
        self.players : List[GPlayer] = players

    def players_to_strings(self) -> str:
        return '\n'.join(f"{i.position}: <@{i.id}> {i.leader and i.leader.civ} {' '.join(f'[**{f}**]' for f in i.flags)}"
                         for i in self.players)

    def players_to_string_with_rank_prevision(self, rankPreviewer) -> str:
        rank_prevision = rankPreviewer.get_ranks_preview(self)
        return '\n'.join(
            f"`{pl.position:2d}: [{rank_prevision[i]:+4.0f}]` <@{pl.id}> {pl.leader and pl.leader.civ} {' '.join(f'[**{f}**]' for f in pl.flags)}"
            for i, pl in enumerate(self.players))

    def get_player_by_id(self, player_id : int) -> GPlayer:
        for i in self.players:
            if i.id == player_id:
                return i

    @staticmethod
    def player_is_quitter(pl : GPlayer) -> bool:
        return "QUIT" in pl.flags

    @staticmethod
    def player_is_subbed(pl : GPlayer) -> bool:
        return "SUBBED" in pl.flags

    @staticmethod
    def player_is_sub(pl : GPlayer) -> bool:
        return "SUB" in pl.flags

    @staticmethod
    def player_is_host(pl : GPlayer) -> bool:
        return "HOST" in pl.flags

    def player_has_win(self, pl : GPlayer) -> bool:
        max_pos = max([i.position for i in self.players])
        return pl.position <= (max_pos / 2)

    def get_ambigous_civs(self) -> Optional[str]:
        r = [i for i in (pl.get_ambigous_civ() for pl in self.players) if i]
        if r:
            return '\n'.join(r)
        return None

    def to_json(self) -> Dict[str, Any]:
        return {
            "gametype": self.gametype and self.gametype.value,
            "players": [i.to_json() for i in self.players]
        }

    @classmethod
    def from_json(cls, js):
        return cls((js['gametype'] and GameType(js['gametype'])) if js['gametype'] else None,
                   [GPlayer.from_json(i) for i in js['players']])

    @classmethod
    def parse_ffa(cls, txt) -> List[GPlayer]:
        # Init
        result = []
        pos = 0
        hosts : List[str] = []
        subs : List[Tuple[str, str]]= []
        txt = txt.split(MODERATOR_TAG, 1)[0]  # Remove after moderator tag
        for line in txt.split('\n'):
            line = line.strip()
            sub_ls = MENTION_SUB.findall(line)
            print(line, sub_ls)
            for player_sub, player_subbed in sub_ls:
                subs.append((player_sub, player_subbed))
            ls = MENTION.findall(line)
            if line.lower().startswith("host"):
                hosts = [discord_id for discord_id, _ in MENTION.findall(line)]
                continue
            # Line is regular report
            pos += 1 if ls else 0
            result.extend(GPlayer(int(discord_id),
                                  leaders.get_leader_named(value),
                                  pos,
                                  (["HOST"] if discord_id in hosts else []) + (["QUIT"] if "quit" in value.lower() else []) +
                                  (["SUB"] if discord_id in [i for i, _ in subs] else []) +
                                  (["SUBBED"] if discord_id in [j for _, j in subs] else []),
                                  value)
                          for discord_id, value in ls)
        result = cls.guess_subs_civs(result, subs)
        return result

    @classmethod
    def parse_teamer(cls, txt) -> List[GPlayer]:
        # Init
        result = []
        pos = 1
        hosts : List[str] = []
        subs : List[Tuple[str, str]]= []
        txt = txt.split(MODERATOR_TAG, 1)[0]  # Remove after moderator tag
        for paraph in txt.split('\n\n'):
            is_team_report = False
            for line in paraph.split('\n'):
                line = line.strip()
                sub_ls = MENTION_SUB.findall(line)
                print(line, sub_ls)
                for player_sub, player_subbed in sub_ls:
                    subs.append((player_sub, player_subbed))
                ls = MENTION.findall(line)
                if line.lower().startswith("host"):
                    hosts = [discord_id for discord_id, _ in MENTION.findall(line)]
                    continue
                # Line is regular report
                if ls:
                    is_team_report = True
                    result.extend(GPlayer(int(discord_id),
                                          leaders.get_leader_named(value),
                                          pos,
                                          (["HOST"] if discord_id in hosts else []) + (["QUIT"] if "quit" in value.lower() else []) +
                                          (["SUB"] if discord_id in [i for i, _ in subs] else []) +
                                          (["SUBBED"] if discord_id in [j for _, j in subs] else []),
                                          value)
                                  for discord_id, value in ls)
            pos += is_team_report
        result = cls.guess_subs_civs(result, subs)
        return result

    @staticmethod
    def guess_subs_civs(result : List[GPlayer], subs : List[Tuple[str, str]]) -> List[GPlayer]:
        players = {str(i.id): i for i in result}
        for gplayer in result:
            if gplayer.leader:
                continue
            for sub, subbed in subs:
                if str(gplayer.id) == sub:
                    gplayer.leader = players[subbed].leader
                    break
                if str(gplayer.id) == subbed:
                    gplayer.leader = players[sub].leader
                    break
        return result

    @classmethod
    def from_str(cls, txt):
        if '\n' in txt:
            gametype_query, corps = txt.split('\n', 1)
        else:
            gametype_query = txt
            corps = ""
        gametype_query = gametype_query.lower().strip()
        gametype = None
        for i in GameType:
            if i.value.lower() in gametype_query:
                gametype = i
                break
        else:
            for k, v in GAMETYPE_ALIAS.items():
                if k in gametype_query:
                    gametype = v
                    break
        if gametype in (GameType.FFA, GameType.PBC):
            players = cls.parse_ffa(corps)
        elif gametype == GameType.TEAMER:
            players = cls.parse_teamer(corps)
        else:
            players = []
            # raise NotFound(f"GameType don't match, please use one of the Following : {', '.join(i.value for i in GameType)}")
        # if not players:
        #     raise InvalidArgs("No player was mentionned in report")
        return cls(gametype, players)


class Match(Report):
    def __init__(self, report_id, gametype, players, validation_msg_id=None):
        self.report_id : int = report_id
        self.validation_msg_id: Optional[int] = validation_msg_id
        Report.__init__(self, gametype, players)

    @classmethod
    def from_message(cls, message, validation_msg_id=None):
        report = Report.from_str(message.content)
        return cls(message.id, report.gametype, report.players, validation_msg_id)

    def to_embed(self, collapsed=True, contest_list=None, rankPreviewer=None):
        if self.gametype:
            title = f"{len(self.players)} players {self.gametype.value}"
        else:
            title = "Unknown gametype"
        contestants = []
        if contest_list:
            contestants = [i.id for i in contest_list if i.id in [p.id for p in self.players]]
        color, warn_msg = self._get_warning(contestants)
        if collapsed:
            description = warn_msg
            if contestants:
                description += '\n\nReport contested by: ' + ', '.join(f"<@{i}>" for i in contestants)
            em = nextcord.Embed(title=title, description=description, color=color)
        else:
            if rankPreviewer:
                description = self.players_to_string_with_rank_prevision(rankPreviewer)
            else:
                description = self.players_to_strings()
            em = nextcord.Embed(title=title, description=description, color=color)
            status_desc = warn_msg
            if contestants:
                status_desc += '\nReport contested by: ' + ', '.join(f"<@{i}>" for i in contestants)
            em.add_field(name="Status", value=status_desc)
        return em


    def _get_warning(self, contestant=None) -> Tuple[Color, Optional[str]]:
        if not self:
            return Color.RED, "Report Parsing failed"
        if not self.gametype:
            return Color.RED, "Report doesn't contain Gametype or he is not reconized"
        if not self.players:
            return Color.RED, "No player are in the report"
        ambigous_msg = self.get_ambigous_civs()
        if ambigous_msg:
            return Color.YELLOW, ambigous_msg
        if not all(i.is_valid() for i in self.players):
            return Color.YELLOW, "Some civilizations have not been recognized"
        if self.gametype == GameType.TEAMER and any([i for i in self.players if i.position not in [1, 2]]):
            return Color.YELLOW, "More than 2 teams in teamer game"
        if (self.gametype == GameType.TEAMER and
            len([i for i in self.players if i.position == 1 and not self.player_is_subbed(i)]) !=
            len([i for i in self.players if i.position == 2 and not self.player_is_subbed(i)])):
            return Color.YELLOW, "Teams didn't have same amount of player"
        # if len(self.players) < 6:
        #     return Color.YELLOW, "Report has suspicious number of player"
        if contestant:
            return Color.PURPLE, "The report is contested by a player"
        if not any(self.player_is_host(i) for i in self.players):
            return Color.GREEN, "No host specified"
        return Color.GREEN, "Report parsed successfully"

    def to_history_message(self, rankPreviewer) -> str:
        header = (f"```Match {self.report_id}; Gametype: {self.gametype.value}; Date: " +
                  nextcord.utils.snowflake_time(self.report_id).strftime("%A %d %B %Y - %H:%M:%S") + "```\n")
        return header + self.players_to_string_with_rank_prevision(rankPreviewer)

    def to_history_line_for_player(self, discord_id : int, client : nextcord.Client=None) -> str:
        for pl in self.players:
            if pl.id == discord_id:
                player = pl
                break
        else:
            return f"ERROR - CAN'T FIND PLAYER IN MATCH {self.report_id}"
        date = nextcord.utils.snowflake_time(self.report_id)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        leader_name = player.leader.civ if player.leader else "???"
        if client:
            leader_emoji = client.get_emoji(player.leader.emoji_id) if player.leader else EMOJI_SPY
            return f"``{self.gametype.value:>6}`` ``{pos_to_str(player.position):>4}`` {leader_emoji} ``{leader_name[:15]:<15}`` ``{date}``"
        else:
            return f"``{self.gametype.value:>6}`` ``{pos_to_str(player.position):>4}`` ``{leader_name[:15]:<15}`` ``{date}``"

    def to_db_entry(self):
        return {'_id': self.report_id, 'validation_msg_id': self.validation_msg_id, 'gametype': self.gametype.value if self.gametype else None,
                'players': [i.to_json() for i in self.players]}

    @classmethod
    def from_db_entry(cls, js):
        return cls(js['_id'], GameType(js['gametype']) if js['gametype'] else None, [GPlayer.from_json(i) for i in js['players']], js['validation_msg_id'])
