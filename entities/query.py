from dataclasses import dataclass


@dataclass
class Query:
    def __init__(self, name: str, tp: int,
                 cls: int, ttl: int, data: str):
        self.name = name
        self.tp = tp
        self.cls = cls
        self.ttl = ttl
        self.data = data
