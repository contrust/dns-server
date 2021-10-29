import binascii
from dataclasses import dataclass


@dataclass
class Question:
    def __init__(self, name: str, tp: int, cls: int):
        self.name = name
        self.tp = tp
        self.cls = cls

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
