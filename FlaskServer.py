from flask import Flask, request
from threading import Thread
import asyncio
import requests
import logging

from config import SERVER_IP, SERVER_PORT, CLIENT_ID, CLIENT_SECRET_PATH
from Modules.Register import RegisterModule
from SteamAPI import SteamAPI

DISCORD_API_BASE = 'https://discord.com/api/v7'
STEAMIO_BASE = 'https://steamid.io/'
STEAM_BASE = 'api.steampowered.com/IPlayerService/GetOwnedGames/v1/'

logger = logging.getLogger("FlaskServer")
logger.setLevel(logging.DEBUG)

class FlaskServer(Thread):
    app = Flask(__name__)
    client = None  # type: CPLBot
    steamApi = SteamAPI()
    with open(CLIENT_SECRET_PATH, 'r') as fd:
        _CLIENT_SECRET = fd.read()


    def __init__(self, client):
        Thread.__init__(self)
        FlaskServer.client = client

    @staticmethod
    @app.route('/', methods=['GET'])
    def register_route():
        client = FlaskServer.client
        code = request.args.get('code')
        if not code:
            return "Code not found in URL"

        state = request.args.get('state')
        if not state:
            return "<b>Error</b><br>Please request a new link from Discord by using .register - this link does not contain your Discord UserID"

        ## Check Oauth2 Token
        oauth_response = requests.post(f'{DISCORD_API_BASE}/oauth2/token',
            data={'client_id': CLIENT_ID, 'grant_type': 'authorization_code', 'client_secret': FlaskServer._CLIENT_SECRET,
                  'code': code, 'scope': "identify connections", "redirect_uri": f"http://{SERVER_IP}:31612"}
        )
        oauth_json = oauth_response.json()
        if oauth_json.get("error"):
            return f"<b>Error</b><br>{oauth_json.get('error')}: {oauth_json.get('error_description')}\nPlease contact a moderator"

        ## Get Discord Profile
        profile_response = requests.get(f'{DISCORD_API_BASE}/users/@me',
                                        headers={'authorization': f"Bearer {oauth_json['access_token']}"})
        profile_json = profile_response.json()
        if profile_json.get("code"):
            return f"<b>Error</b><br>{profile_json.get('code')}"
        if profile_json.get('id') != request.args.get('state'):
            return "<b>Error</b><br>You are logged into two different Discord accounts - one on the website and one in your app. Log out of the website and try again or try again from the website."

        ## Get Steam Connection
        connections_response = requests.get(f"{DISCORD_API_BASE}/users/@me/connections",
                                            headers={'authorization': f"Bearer {oauth_json['access_token']}"})
        connections_json = connections_response.json()
        if isinstance(connections_json, dict) and connections_json.get("code", None):
            return f"<b>Error</b><br>{connections_json.get('code', None)}"

        i = [js['id'] for js in connections_json if js['type'] == 'steam']
        if not i or not i[0]:
            return f"<b>Error</b><br>Your steam account does not seem to be linked to discord. Please close this window and step through the instructions again"
        discord_steam_id = i[0]
        # Steamid.io request
        steamio_response = requests.get(f"{STEAMIO_BASE}/lookup/{discord_steam_id}")
        steam_id = int(steamio_response.content.split(b'data-steamid64')[1].split(b'"')[1])
        logger.info(f"Get Steamid64: {steam_id}")
        # Check if ID is already in database
        player = client.database.get_player_by_steam_id(steam_id)
        if player:
            return "This Steam account is already registered"
        # Steam request
        minutes = asyncio.run(FlaskServer.steamApi.get_total_number_of_civ6_minutes_play(steam_id))
        logger.info(f"Player played {minutes} minutes at Civ6")
        if not minutes:
            return "<b>Error:</b><br>You have your steam profile set to private, please make it public to allow the bot to verify you own the game and have at least 2 hours of playing."
        if minutes < 120:
            return "<b>Error:</b><br>You either need more than 2 hours of Civ 6 play time or must change a Steam setting. Please close this page and return to Discord for further instructions."
        # Send to the discord Module
        registerModule = client.get_module(RegisterModule)
        client.loop.create_task(registerModule.register_player(profile_json['id'], steam_id))
        return "Your registration was complete, Welcome to Civ Player League.<br>You can now close this page"

    @staticmethod
    @app.route('/join/<string:game>/<string:player>/<string:session>', methods=['GET'])
    def join_route(game, player, session):
        return f"<script>window.location.href = 'steam://joinlobby/{game}/{player}/{session}'</script>"

    def run(self):
        self.app.run(SERVER_IP, SERVER_PORT, use_reloader=False)


