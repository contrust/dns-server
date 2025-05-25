import binascii
from dataclasses import dataclass


@dataclass
class Question:
    def __init__(self, name: str, tp: int, cls: int):
        self.name = name
        self.tp = tp
        self.cls = cls

    def to_tuple(self):
        return (self.name, self.tp, self.cls)

    def __hash__(self):
        return hash((self.name, self.tp, self.cls))

    def __eq__(self, other):
        if not isinstance(other, Question):
            return False
        return (self.name, self.tp, self.cls) == (
            other.name, other.tp, other.cls)

    def __str__(self):
        result = ""
        for part in self.name.split("."):
            result += "{:02x}".format(len(part))
            result += (binascii.hexlify(part.encode('iso8859-1')).
                       decode('iso8859-1'))
        result += "00"
        result += "{:04x}".format(self.tp)
        result += "{:04x}".format(self.cls)
        return result
