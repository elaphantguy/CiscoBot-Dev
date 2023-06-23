from abc import ABC, ABCMeta, abstractmethod
from typing import Dict, List, Callable

from Database import Database

class abcModule(ABC):
    def __init__(self, client):
        self.client = client  # type: CPLBot
        self.database : Database = client.database
        self.commands : Dict[str, Callable] = {}
        self.dependency : List[abcModule] = []
        self.events : Dict[str, List[Callable]] = {}

    async def on_ready(self):
        return