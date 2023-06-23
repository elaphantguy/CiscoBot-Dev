from pymongo import MongoClient
from typing import Optional, Union, List, Generator
from datetime import datetime, timezone
import logging

from exc import AlreadyExist, NotFound
from utils import get_discord_id_from_date
from models.DbModel import Player, PlayerStats1, PlayerStats2, Suspension
from models.ReportParser import Match

logger = logging.getLogger("Database")

class Database(MongoClient):
    def __init__(self):
        with open("private/mongo_creds") as fd:
            super().__init__(fd.read())

    def get_player_by_discord_id(self, discord_id : Union[int, str]) -> Optional[Player]:
        player = self.players.players.find_one({'discord_id': str(discord_id)})
        if player:
            return Player(player)
        return None

    def get_player_by_steam_id(self, steam_id : Union[int, str]) -> Optional[Player]:
        player = self['players']['players'].find_one({'steam_id': str(steam_id)})
        if player:
            return Player(player)
        return None

    def register_player(self, discord_id : Union[int, str], steam_id : Union[int, str], name : str="") -> Player:
        if self.get_player_by_discord_id(discord_id) is not None:
            raise AlreadyExist("The user already Exist")
        player = Player.from_ids(discord_id, steam_id, name)
        self['players']['players'].insert_one(player.to_json())
        logger.info(f"Register Player: discord_id={discord_id}, steam_id={steam_id}, name={name}")
        return player

    def get_all_playerstats(self, gameType : str, min_games : int=3) -> List[PlayerStats2]:
        cursor = self['stats2'][gameType].find({'games': {'$gte': min_games}})
        return [PlayerStats2(i, gameType=gameType) for i in cursor]
    
    def get_all_season_playerstats(self, gameType : str, min_games : int=3) -> List[PlayerStats2]:
        cursor = self['current_season'][gameType].find({'games': {'$gte': min_games}})
        return [PlayerStats2(i, gameType=gameType) for i in cursor]

    def get_playerstats_by_id(self, gameType : str, discord_id : Union[int, str], table : str = 'stats2') -> PlayerStats2:
        playerStats = self[table][gameType].find_one({'_id': int(discord_id)})
        if playerStats:
            return PlayerStats2(playerStats, gameType=gameType)
        return PlayerStats2({}, gameType=gameType, create_id=discord_id)

    def get_legacy_playerstats_by_id(self, gameType : str, discord_id : Union[int, str]) -> Optional[PlayerStats1]:
        playerStats = self['stats'][gameType].find_one({'_id': str(discord_id)})
        if playerStats:
            return PlayerStats1(playerStats, gameType=gameType)
        return None

    def set_playerstats(self, playerstats : PlayerStats2, table : str = 'stats2'):
        playerstats.lastModified = datetime.now(tz=timezone.utc)
        self[table][playerstats.gameType].replace_one({'_id': playerstats.id}, playerstats.to_json(), upsert=True)

    def add_match(self, match : Match):
        print (self['matchs'])
        self['matchs']['waiting'].insert_one(match.to_db_entry())

    def _get_row_match(self, match_id : int):
        return self['matchs']['waiting'].find_one({'$or': [{'_id': match_id}, {'validation_msg_id': match_id}]})

    def get_match(self, match_id : int) -> Optional[Match]:
        match = self._get_row_match(match_id)
        if match:
            return Match.from_db_entry(match)
        return None

    def get_match_history_from(self, date : datetime) -> List[Match]:
        raw_matchs = self['matchs']['validated'].find( {'_id': {'$gte': get_discord_id_from_date(date)} } )
        return [Match.from_db_entry(i) for i in raw_matchs]

    def get_match_history_for_player(self, discord_id : int) -> List[Match]:
        raw_matchs = self['matchs']['validated'].find( {"players.id": discord_id} ).sort("_id", -1)
        return [Match.from_db_entry(i) for i in raw_matchs]

    def edit_match(self, match_id : int, match : Match):
        old_match = self.get_match(match_id)
        if not old_match:
            raise NotFound(f"Can't find matchId {match_id} in database")
        self['matchs']['waiting'].replace_one({'_id': old_match.report_id}, match.to_db_entry())

    def delete_match(self, match_id : int):
        match = self.get_match(match_id)
        self['matchs']['waiting'].delete_one({'_id': match.report_id})

    def valid_match(self, match_id : int) -> Optional[Match]:
        match = self.get_match(match_id)
        if not match:
            return None
        self['matchs']['validated'].insert_one(match.to_db_entry())
        self['matchs']['waiting'].delete_one({'_id': match.report_id})
        return match

    def get_suspension(self, player_id : int) -> Optional[Suspension]:
        suspension = self['players']['suspensions2'].find_one({'_id': player_id})
        if suspension:
            return Suspension(suspension)
        return None

    def set_suspension(self, suspension : Suspension):
        suspension.lastModified = datetime.now(tz=timezone.utc)
        self['players']['suspensions2'].replace_one({'_id': suspension.id}, suspension.to_json(), upsert=True)

    def get_all_suspended_players(self) -> List[Suspension]:
        suspended = self['players']['suspensions2'].find({'is_suspended': True})
        return [Suspension(i) for i in suspended]