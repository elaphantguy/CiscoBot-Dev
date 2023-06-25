import csv
import re
import logging
from typing import List

from config import LEADER_CSV_PATH

logger = logging.getLogger("LeaderParser")
NON_WORD = re.compile(r"[^\wÀ-ú\-]+")
TYPES_OF_CIV = ['naval', 'culture', 'science', 'war', 'generalist', 'monumentality']

class Leaders:
    def __init__(self, leaders_):
        self.leaders = leaders_

    def __getitem__(self, item):
        return self.leaders[item]

    def __iter__(self):
        for i in self.leaders:
            yield i

    def _get_leader_named(self, name):
        result = [leader for leader in self if leader == name]
        if len(result) > 1:
            logger.warning(f"Receive multiple leader for query: {name} => {result}")
            return None
        if result:
            return result[0]
        return None

    def get_leader_named(self, name):
        if name is None:
            return None
        name = name.lower()
        leader = self._get_leader_named(name)
        if leader:
            return leader
        for i in NON_WORD.split(name):
            leader = self._get_leader_named(i)
            if leader:
                return leader
        return None

    def get_leader_by_emoji_id(self, emoji_id : int):
        for leader in self:
            if leader.emoji_id == emoji_id:
                return leader
        return None

    def get_leader(self, leader_uuid):
        for leader in self:
            if leader.uuname == leader_uuid:
                return leader
        return None

class Leader:
    def __init__(self, emoji_id, uuname, civ, *alias):
        self.emoji_id = int(emoji_id)
        self.uuname = uuname
        self.civ = civ
        self.type_of_civ = 'generalist'
        has_a_civ_type = [item for item in alias if item in TYPES_OF_CIV]
        if (len(has_a_civ_type) > 0):
           self.type_of_civ = has_a_civ_type[0]
        self.alias = [item for item in alias if item not in TYPES_OF_CIV]
        self.all_name = [i.lower() for i in [uuname, civ, *self.alias]]

    def __repr__(self):
        return f"<Leader: {self.uuname}>"

    def __eq__(self, other):
        if other is None:
            return False
        if isinstance(other, str):
            return other.lower() in self.all_name
        elif isinstance(other, Leader):
            return self.uuname == other.uuname
        raise TypeError(f"Can't use Leader.__eq__ with {type(other)}")

    def __lt__(self, other):
        return str(self) < str(other)

    def __str__(self):
        return self.to_string()

    def to_string(self):
        return self.civ

def load_leaders() -> Leaders:
    logger.info("Loading " + LEADER_CSV_PATH)
    with open(LEADER_CSV_PATH, "r") as fd:
        leaders_array = csv.reader(fd, delimiter=',')
        leaders_ = Leaders([Leader(*leader_array) for leader_array in leaders_array])
    return leaders_

leaders = load_leaders()