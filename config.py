### DO NOT EDIT THIS PART ###
from sys import argv
from constant import *
from enum import Enum
from datetime import timedelta
from typing import Dict, List, Tuple, Callable, Any

import trueskill

DEBUG_MODE = "--debug" in argv[1:]
# type definition
EMOJI = str
LOWERCASE_STR = str
#############################

# Bot credentials
CLIENT_ID = 1075739307144388659
CLIENT_SECRET_PATH = 'private/client_secret'
TOKEN_PATH = "private/token_cplbot"

# General
COMMAND_PREFIX = "."
DEVELOPPER_CONTACT = "<@384274248799223818>"
CPL_GUILD_ID = 1087477187898261605
MODERATOR_ROLE_ID = 1121396594894446694
ADMIN_ROLE_ID = 1121396594894446694
BOT_PROGRAMMER_ROLE_ID = 489447573736914946
CAN_USE_DBG_COMMAND = [ADMIN_ROLE_ID, BOT_PROGRAMMER_ROLE_ID]
CAN_USE_ADMIN_COMMAND = [ADMIN_ROLE_ID, BOT_PROGRAMMER_ROLE_ID]

# Auto-moderator
NO_COMMANDS_CHANNELS = [291751672106188800, 413532530268962816]
SPECIFIC_CHANNEL_COMMAND : Dict[str, List[int]] = {
    "vote": [1121398399699259452],
    "teamvote": [1121398399699259452]
}

# Report
REPORT_CHANNEL_ID = 1121396327851503647
HISTORY_CHANNEL_ID = 1121397779336527922
#  All text after this will be ignored by report parser
MODERATOR_TAG = "<@&1121396594894446694>"

# Register
SERVER_IP = "51.68.123.207"
SERVER_PORT = "31612"
OAUTH_LINK_BASE = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri=http%3A%2F%2F{SERVER_IP}:{SERVER_PORT}&response_type=code&scope=identify%20connections&state="
WELCOME_CHANNEL = 368928122219003904
NEW_REGISTERED_LOG_CHANNEL = 615805208848498688
ROLES_WHEN_REGISTED = [615780983047979008, 628464552882995200, 444330435070132235, 577702305999093763]

# Ban
SUSPENDED_ROLE_ID = 294099361053540353
GREAT_PEOPLE_ROLE_ID = 761095033738362921
SUSPENDED_PLAYER_CHANNEL_ID = 507906789984174090
SUSPENSIONS_TYPE_TIERS = {
    "quit": 1,
    "minor": 1,
    "moderate": 2,
    "major": 4,
}
QUIT_APPLY_BASIC_SUSPENSION = True
QUIT_SUSPENSION_TIME = [1, 2, 3, 5, 8, 13, 21, 34, 55, 180]  # Only Used if QUIT_APPLY_BASIC_SUSPENSION is False
SUSPENSION_TIME = [1, 2, 3, 5, 8, 13, 21, 34, 55, 180]
DAY_TO_PERMA = 180
GAME_TO_DECAY_TIER = 30
TIME_TO_DECAY_TIER = timedelta(days=45)
REPORT_APPLY_QUIT = False
REPORT_APPLY_OVERSUB = True
OVERSUB_PENALTY_TIER = "minor"
GAME_TO_GREAT_PEOPLE = 50

# Ranked
RANKED_ROLE = 1121857779188113438
RANKS_ROLES : List[Tuple[str, int, int]] = [
    ("Deity", 1121858542358495274, 2000),
    ("Immortal", 1121858498083438654, 1800),
    ("Emperor", 1121858452935938199, 1600),
    ("King", 1121858433499533322, 1500),
    ("Prince", 1121858362120872036, 1400),
    ("Warlord", 1121858359222599730, 1300),
    ("Chieftain", 1121858301047611542, 1200),
    ("Settler", 1121858260098625556, 1100),
    ("Builder", 1121858210140270642, 1000),
    ("Scout", 1121858141206880286, 0)
]

# TrueSkill Ranking
MU = 1250
SIGMA = 150
BETA = 400
TAU = 10

QUITTER_MAX_POINT = -50
SUBBED_MAX_POINT = 0
SUB_MINIMUM_POINT = 5
DONT_CHANGE_SIGMA_ON_PENALTIES = True

def SKILL(rating : trueskill.Rating, teamer=False) -> float:
    if teamer:
        return rating.mu - max(rating.sigma - 100, 0) + (rating.mu - MU) * 2
    return rating.mu - max(rating.sigma - 100, 0)

LEADERBOARDS : Dict[str, Dict[str, Any]]= {
    'FFA': {'channel_id': 1087478587864658001,
            'message_id': [1120120275586011196, 1120120281957158912, 1120120286612824094, 1120120289729196042, 1120120300441440346,
                            1120120349854543942, 1120120356116631562, 1120120377826349117, 1120120382402351154, 1120120387485847615]},
    'Teamer': {'channel_id': 1087478557422399548,
                'message_id': [1120120398122602567, 1120120408696426526, 1120120417252823130, 1120120426304122940, 1120120436626305184,
                            1120120445065236540, 1120120452631756840, 1120120459854348408, 1120120494960693290, 1120120505521946654]},
    'PBC': {'channel_id': 1120325170750562334,
            'message_id': [1120325269757100193, 1120325281643774022, 1120325293517840464, 1120325308957069354, 1120325318545252362,
                            1120325336371044382, 1120325346072477766, 1120325352078704732, 1120325356986044456, 1121427604797403197]}
}
SEASON_LEADERBOARDS : Dict[str, Dict[str, Any]]= {
    'FFA': {
        'channel_id': 1087478528011927633,
        'message_id': [
            1108747905688408064, 1108747949493723176, 1108764181211123764, 1109862221368012822, 1109862687908823121,
            1109949992451444769, 1109950024227496120, 1109951021565886518, 1109951053589401630, 1109952121807327353
        ]
    },
    'Teamer': {
        'channel_id': 1121529668374372382,
        'message_id': [
            1121529778466471996, 1121529798372626493, 1121529800876621906, 1121529803032494251, 1121529804609552405,
            1121529806073368658, 1121529818480132227, 1121529844098924645, 1121529886742417528, 1121529978459258931
        ]
    },
    'PBC': {
        'channel_id': 1121529727044292728,
        'message_id': [
            1121530013703995523, 1121530016530956459, 1121530021014671460, 1121530025812971570, 1121530027679432734,
            1121530031227809852, 1121530034436448359, 1121530038731419810, 1121530041923281058, 1121530045912068186
        ]
    }
}

# leaders
LEADER_CSV_PATH = "public_data/leaders.csv"
AMBIGOUS_QUERY : Dict[LOWERCASE_STR, List[str]] = {
    "america": ["Teddy-RR", "Teddy-BM"],
    "teddy": ["Teddy-RR", "Teddy-BM"],
    "england": ["Victoria", "Eleanor-En"],
    "france": ["Catherine-BQ", "Catherine-Magnificent", "Eleanor-Fr"],
    "greece": ["Pericles", "Gorgo"],
    "india": ["Gandhi", "Chandragupta"],
    "china": ["Qin-Shi", "Kublai-China"],
    "mongolia": ["Genghis-Khan", "Kublai-Mongolia"],
    "kublai": ["Kublai-Mongolia", "Kublai-China"],
    "eleanor": ["Eleanor-En", "Eleanor-Fr"]
}
USE_FIRST_LEADER_IF_AMBIGOUS = False

# Draft / VOTE
MINUTES_BEFORE_REMOVING_VOTE = 15
DRAFT_MODE_TITLE = "Draft Mode"
class DraftMode(Enum):
    WITH_TRADE = "Trade Allowed"
    NO_TRADE = "Trade Forbidden"
    BLIND = "Blind"
    RANDOM = "All Random"
    DRAFT_2 = "Draft 2"
    CWC = "CWC"
    DDRAFT_9_3_1 = "Dynamic 9 3 1"

VOTE_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "Communication": [(EMOJI_NO_ENTRY, "None"), (LETTER.F, "Private between Friends and Allies"), (LETTER.P, "All Private Allowed"), (EMOJI_PLUS, "All Public Only")],
    "Official Friends/Allies": [(NB[0], "None"), (NB[1], "One"), (NB[2], "Two"), (EMOJI_INFINITY, "Unlimited")],
    "BYC Enabled (Capitals Only)": [(EMOJI_OK, "Yes "), (EMOJI_NO_ENTRY, "No")],
    "Game Duration": [(NB[4], "4 Hours"), (NB[6], "6 Hours"), (EMOJI_INFINITY, "Unlimited")],
    "Map": [(LETTER.P, "Pangea"), ("🏝", "Contient & Island"), (NB[7], "7 seas"), (LETTER.H, "Highland"), (LETTER.L, "Lakes"), ("🗾", "Archipelago"),
            (LETTER.F, "Fractal"), ("🗺️", "Small Continents"), ("🌋", "Primordial"), (LETTER.T, "Tilted Axis"), ("🌊", "Inland Sea"), ("💦", "Wetlands"), ("❓", "Random")],
    "Disasters": [(NB[0], "0"), (NB[1], "1"), (NB[2], "2"), (NB[3], "3"), (NB[4], "4")],
    "CC Voting": [(EMOJI_DOWN, "10 Turns Earlier"), (EMOJI_NEUTRAL, "No Change"), (EMOJI_UP, "10 Turns Later"), (EMOJI_DOUBLE_UP, "20 Turns Later")],
    DRAFT_MODE_TITLE: [("✅", DraftMode.WITH_TRADE.value), ("🚫", DraftMode.NO_TRADE.value), ("🙈", DraftMode.BLIND.value), ("❓", DraftMode.RANDOM.value)]
}
DEFAULT_VOTE_SETTINGS: Dict[str, str] = {
    "Gold Trading ": 'Not Allowed',
    "Luxuries Trading ": 'Allowed',
    "Strategics Trading ": 'Not Allowed',
    "Military Alliance ": 'Not Allowed',
    "Timer ": 'Competitive',
    'Resources ': 'Abundant',
    'Strategics ': 'Abundant',
    'Ridges Definition ': 'Classic',
    'Wonders ': 'Standard'
}
TEAM_VOTE_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "1 Remap Token Per Team (T10)": [(EMOJI_OK, "Yes "), (EMOJI_NO_ENTRY, "No")],
    "BYC Enabled (Capitals Only)": [(EMOJI_OK, "Yes "), (EMOJI_NO_ENTRY, "No")],
    "Map": [(LETTER.P, "Pangea"), ("🏝", "Contient & Island"), (NB[7], "7 seas"), (LETTER.H, "Highland"), (LETTER.L, "Lakes"), ("🗾", "Archipelago"),
            (LETTER.F, "Fractal"), ("🗺️", "Small Continents"), ("🌋", "Primordial"), (LETTER.T, "Tilted Axis"), ("🌊", "Inland Sea"), ("💦", "Wetlands"), ("❓", "Random")],
    "Timer": [("🐌", "Casual"), ("🕑", "Dynamic"), ("⏩", "Competitive")],
    "Ressources": [(LETTER.S, "Standard"), (LETTER.A, "Abundant")],
    "Strategics": [(LETTER.S, "Standard"), (LETTER.A, "Abundant"), (LETTER.E, "Epic"), (LETTER.G, "Guaranteed")],
    "Ridges definition": [(LETTER.S, "Standard"), (LETTER.C, "Classic"), (LETTER.L, "Large opening"), (LETTER.I, "Impenetrable")],
    "Disasters": [(NB[0], "0"), (NB[1], "1"), (NB[2], "2"), (NB[3], "3"), (NB[4], "4")],
    "Wonders": [(EMOJI_NO_ENTRY, "None"), (EMOJI_DOWN, "Scarse"), (EMOJI_NEUTRAL, "Standard"), (EMOJI_UP, "Abundant")],
    DRAFT_MODE_TITLE: [(NB[2], DraftMode.DRAFT_2.value), ("🌍", DraftMode.CWC.value), (NB[9], DraftMode.DDRAFT_9_3_1.value), ("❓", DraftMode.RANDOM.value)]
}
SECRET_CC_VOTE_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "CC to": 
    [(EMOJI_OK, "Yes"), (EMOJI_NO, "No")],
}
SECRET_IRREL_VOTE_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "Irrel": 
    [(EMOJI_OK, "Yes"), (EMOJI_NO, "No")],
}
SECRET_SCRAP_VOTE_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "Scrap": 
    [(EMOJI_OK, "Yes"), (EMOJI_NO, "No")],
}
SECRET_REMAP_VOTE_SETTING : Dict[str, List[Tuple[EMOJI, str]]] = {
    "Remap" :
    [(EMOJI_OK, "Yes"), (EMOJI_NO, "No")]
}


if DEBUG_MODE:
    CLIENT_ID = 427867039135432714
    CLIENT_SECRET_PATH = 'private/client_secret_eldenbot'
    TOKEN_PATH = "private/token_eldenbot"
    COMMAND_PREFIX = "cpl/"
    SERVER_IP = "127.0.0.1"
    OAUTH_LINK_BASE = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri=http%3A%2F%2F{SERVER_IP}:{SERVER_PORT}&response_type=code&scope=identify%20connections&state="
    REPORT_CHANNEL_ID = 834418663674740767
    HISTORY_CHANNEL_ID = 507906789984174090
