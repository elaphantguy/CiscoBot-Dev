import aiohttp
import logging

from typing import Dict, Optional, Any

logger = logging.getLogger('SteamAPI')

class SteamAPI:

    CIV6_GAME_ID = 289070
    OWNED_GAME_URL = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={key}&steamid={steam_id}"

    def __init__(self):
        with open("private/steam_creds") as fd:
            self._api_key = fd.read()

    async def get_owned_games(self, steam_id) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.OWNED_GAME_URL.format(steam_id=steam_id, key=self._api_key)) as response:
                return await response.json()

    async def get_total_number_of_minutes_played(self, steam_id, app_id) -> Optional[int]:
        """Return number of minutes the player has played the game, return None if not found"""
        js = await self.get_owned_games(steam_id)
        resp = js.get('response', None)
        if resp is None:
            logger.warning(f"response not found in js returned for steamid={steam_id} and app_id={app_id}.")
            logger.debug(f"Got: {resp}")
            return None
        if not resp.get('game_count', 0):
            logger.info(f"No game was found for steamid={steam_id} and app_id={app_id}")
            return None
        games = [i for i in resp['games'] if i['appid'] == app_id]
        if not games:
            logger.info(f"Game id {app_id} not found for steam id {steam_id}")
            return None
        return games[0]['playtime_forever']

    async def get_total_number_of_civ6_minutes_play(self, steam_id) -> Optional[int]:
        """Return number of minutes the player has played civ6, return None if civ6 is not found"""
        return await self.get_total_number_of_minutes_played(steam_id, self.CIV6_GAME_ID)

