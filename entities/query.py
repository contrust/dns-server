import binascii
import socket
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

    def __str__(self):
        result = ""
        for part in self.name.split("."):
            result += "{:02x}".format(len(part))
            result += (binascii.hexlify(part.encode('iso8859-1')).
                       decode('iso8859-1'))
        result += "00"
        result += "{:04x}".format(self.tp)
        result += "{:04x}".format(self.cls)
        result += "{:08x}".format(self.ttl)
        data = self.data
        if self.tp == 1:
            data = socket.inet_aton(self.data).decode('iso8859-1')
        elif self.tp == 28:
            data = socket.inet_pton(socket.AF_INET6, self.data).decode('iso8859-1')
        result += "{:04x}".format((len(data) + (2 if self.tp not in {1, 28} else 0)))
        for part in data.split("."):
            if self.tp not in {1, 28}:
                result += "{:02x}".format(len(part))
            result += (binascii.hexlify(part.encode('iso8859-1')).
                       decode('iso8859-1'))
        if self.tp not in {1, 28}:
            result += "00"
        return result

