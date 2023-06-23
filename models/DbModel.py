import nextcord
import trueskill
from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict
CIV_UUID = str


from exc import BotException
from config import MU, SIGMA, SKILL, QUIT_APPLY_BASIC_SUSPENSION, GAME_TO_GREAT_PEOPLE

class Player:
    def __init__(self, dic):
        self.discord_id : str = dic.get('discord_id')
        self.steam_id: str = dic.get('steam_id')
        self.user_name: str = dic.get('user_name')
        self.display_name: str = dic.get('display_name')

    def __dict__(self):
        return {'discord_id': self.discord_id, 'steam_id': self.steam_id, 'user_name': self.user_name,
                'display_name': self.display_name}

    def to_embed(self) -> nextcord.Embed:
        return nextcord.Embed(title=self.user_name, description=f"name: {self.display_name}\nsteam id: {self.steam_id}")

    def to_json(self):
        return self.__dict__()

    @classmethod
    def from_ids(cls, discord_id, steam_id, name=""):
        return cls({'discord_id': str(discord_id), 'steam_id': str(steam_id), 'user_name': name, 'display_name': name})

class Suspension:
    def __init__(self, dic):
        self._id = dic.get('_id')
        self.end = dic.get('end', None)
        self.is_suspended = dic.get('is_suspended', False)
        self.tier = dic.get('tier', 0)
        self.quit_tier = dic.get('quit_tier', 0)
        self.game_without_penalty = dic.get('game_without_penalty', 0)
        self.next_decay_games = dic.get('game_without_penalty', None)
        self.next_decay_timestamp = dic.get('game_without_penalty', None)
        self.history : List[str] = dic.get('history', [])
        self.last_modified = dic.get('last_modified', None)

    def to_embed(self, member=None) -> nextcord.Embed:
        statlist: List[Tuple[str, ...]] = [
            ('Suspended', f"{self.is_suspended}"),
            ('Suspension end', f"{self.end}"),
            ('Suspension tier', f"{self.tier}"),
            ('Game w/o penalty', f"{self.game_without_penalty}"),
        ]
        if self.tier:
            t : timedelta = self.next_decay_timestamp - datetime.now(tz=timezone.utc)
            statlist += [
            ('Game until decay', f"{max(self.next_decay_games - self.game_without_penalty, 0)}"),
            ('Time until decay', f"{0 if t < timedelta() else t.days+1} day(s)"),
            ]
        max_length = max(len(i) for i, _ in statlist)
        em = nextcord.Embed(title="Suspension Stats",
                           description='\n'.join(f"`{i:>{max_length}}`: {j}" for i, j in statlist),
                           colour=member.colour if member else 0)
        return em

    @property
    def id(self):
        return self._id

    def can_decay(self):
        return (not self.is_suspended and self.next_decay_timestamp and self.next_decay_games
                and self.game_without_penalty > self.next_decay_games and datetime.now(tz=timezone.utc) > self.next_decay_timestamp)

    def is_great_people(self):
        return self.tier == 0 and (self.quit_tier == 0 or QUIT_APPLY_BASIC_SUSPENSION) and self.game_without_penalty >= GAME_TO_GREAT_PEOPLE

    def to_json(self):
        return self.__dict__


class PlayerStats2(trueskill.Rating):
    def __init__(self, dic, gameType=None, create_id=None):
        self.gameType = gameType
        self._id = dic.get('_id')
        if not self._id:
            if not create_id:
                raise BotException("The field _id wasn't found and not provided.")
            self._id = int(create_id)

        # TrueSkill Rating
        trueskill.Rating.__init__(self, mu=dic.get('mu', MU), sigma=dic.get('sigma', SIGMA))

        # General stats
        self.games = dic.get('games', 0)
        self.wins = dic.get('wins', 0)
        self.first = dic.get('first', 0)

        # Subs
        self.subbedIn = dic.get('subbedIn', 0)
        self.subbedOut = dic.get('subbedOut', 0)

        # Complex stats
        self.civs : Dict[CIV_UUID, int] = dic.get('civs', {})

        # Metadata
        self.lastModified = dic.get('lastModified', None)

    @property
    def id(self):
        return self._id

    @property
    def skill(self) -> float:
        return SKILL(self.get_rating(), teamer=self.gameType=="Teamer")

    def is_oversub(self) -> bool:
        return True

    def get_rating(self):
        return trueskill.Rating(mu=self.mu, sigma=self.sigma)

    def to_json(self):
        return {'_id': self._id, 'mu': self.mu, 'sigma': self.sigma, 'games': self.games, 'wins': self.wins, 'first': self.first,
                'subbedIn': self.subbedIn, 'subbedOut': self.subbedOut, 'civs': self.civs, 'lastModified': self.lastModified}

    def create_embed_field(self, em : nextcord.Embed):
        statlist: List[Tuple[str, ...]] = [
            ('Skill', f"{self.skill:.0f}"),
            ('TS Mu', f"{self.mu:.0f}"),
            ('TS Sigma', f"{self.sigma:.0f}"),
            # ('Win %', f'{self.wins / self.games:.1%}'),
            ('Games', f"{self.games}"),
            ('Wins', f"{self.wins}"),
            ('1st', f"{self.first}"),
            ('Sub In', f"{self.subbedIn}"),
            ('Sub Out', f"{self.subbedOut}"),
        ]
        max_length = max(len(i) for i, _ in statlist)
        em.add_field(name=self.gameType, value='\n'.join(f"`{i:>{max_length}}`: {j}" for i, j in statlist))

    def to_embed(self, member=None):
        em = nextcord.Embed(title="Stats", description=f"Stat for <@{self.id}>", colour=member.colour if member else 0)
        self.create_embed_field(em)
        return em



class PlayerStats1:
    def __init__(self, dic, gameType=None):
        self.gameType = gameType
        self.id = dic.get('_id')
        self.rating = dic.get('rating')
        self.rd = dic.get('rd')
        self.vol = dic.get('vol')
        self.tau = dic.get('tau')
        self.lastChange = dic.get('lastChange')
        self.games = dic.get('games')
        self.wins = dic.get('wins')
        self.losses = dic.get('losses')
        self.subbedIn = dic.get('subbedIn')
        self.subbedOut = dic.get('subbedOut')
        self.ressets = dic.get('ressets')
        self.civs = dic.get('civs')
        self.lastModified = dic.get('lastModified')
        self.first = dic.get('first', 0)

    def create_embed_field(self, em : nextcord.Embed):
        statlist: List[Tuple[str, ...]] = [
            ('Skill', f"{self.rating}"),
            ('Games', f"{self.games}"),
            ('Win %', f"{self.wins / self.games:.1%}"),
            ('1st', f"{self.first}"),
            ('Wins', f"{self.wins}"),
            ('Losses', f"{self.losses}"),
            ('Sub In', f"{self.subbedIn}"),
            ('Sub Out', f"{self.subbedOut}"),
            ('RD', f"{self.rd:.2f}"),
        ]
        max_length = max(len(i) for i, _ in statlist)
        em.add_field(name=self.gameType, value='\n'.join(f"`{i:>{max_length}}`: {j}" for i, j in statlist))

    def to_embed(self, member=None):
        em = nextcord.Embed(title="Stats", description=f"Stat for <@{self.id}>", colour=member.colour if member else 0)
        self.create_embed_field(em)
        return em