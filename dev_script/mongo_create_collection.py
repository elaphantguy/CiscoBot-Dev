from pymongo import MongoClient
import trueskill

MU = 1400
SIGMA = MU / 3
BETA = SIGMA / 2
TAU = SIGMA / 100

env = trueskill.TrueSkill(mu=MU, sigma=SIGMA, beta=BETA, tau=TAU, draw_probability=0.01)
myclient = MongoClient("mongodb://localhost:27017/")

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

    def get_rating(self) -> trueskill.Rating:
        return trueskill.Rating(mu=self.rating, sigma=self.rd)


statsDb = myclient["stats"]
ffa = statsDb["ffa"]
users = [PlayerStats1(d, gameType='ffa') for d in ffa.find()]

users.sort(key=lambda i: i.get_rating().exposure, reverse=True)

print(*[
    f"``#{i + 1}: exp: {int(pl.get_rating().exposure)} rate: {int(pl.rating)} RD: {int(pl.rd)}`` <@{pl.id}> ({pl.wins}/{pl.losses})"
    for i, pl in enumerate(users[:100])], sep='\n')