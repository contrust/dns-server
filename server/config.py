# server/config.py
import json
from dataclasses import dataclass


@dataclass
class Config:
    def __init__(self):
        self.hostname = '127.0.0.2'
        self.port = 53
        self.max_threads = 5
        self.cache_size = 100
        self.log_file = 'log.txt'
        self.cache_file = 'cache.pkl'
        self.proxy_hostname = "a.root-servers.net"
        self.proxy_port = 53

    def load(self, path: str) -> None:
        with open(path) as json_file:
            data = json.load(json_file)
            self.__dict__.update(data)

    def unload(self, path: str) -> None:
        with open(path, mode='w') as file:
            json.dump(self.__dict__, file, indent=4)
