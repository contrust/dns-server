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
    

    def __hash__(self):
        return hash((self.name, self.tp, self.cls, self.data))

    def __eq__(self, other):
        if not isinstance(other, Query):
            return False
        return (self.name, self.tp, self.cls, self.data) == (
            other.name, other.tp, other.cls, other.data
        )

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
            data = socket.inet_pton(socket.AF_INET, self.data)\
                .decode('iso8859-1')
        elif self.tp == 28:
            data = socket.inet_pton(socket.AF_INET6, self.data)\
                .decode('iso8859-1')
        result += "{:04x}".format((len(data) +
                                   (2 if not is_ip_type(self.tp) else 0)))
        if is_ip_type(self.tp):
            result += (binascii.hexlify(data.encode('iso8859-1')).
                       decode('iso8859-1'))
        else:
            for part in data.split('.'):
                result += "{:02x}".format(len(part))
                result += (binascii.hexlify(part.encode('iso8859-1')).
                           decode('iso8859-1'))
            result += "00"
        return result


def is_ip_type(number: int) -> bool:
    return number in {1, 28}
