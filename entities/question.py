import binascii
from dataclasses import dataclass


@dataclass
class Question:
    def __init__(self, qcount: int, ancount: int, nscount: int, arcount: int,
                 name: str, qtype: int, qclass: int):
        self.qcount = qcount
        self.ancount = ancount
        self.nscount = nscount
        self.arcount = arcount
        self.name = name
        self.qtype = qtype
        self.qclass = qclass

    def __str__(self):
        result = ""
        result += "{:04x}".format(self.qcount)
        result += "{:04x}".format(self.ancount)
        result += "{:04x}".format(self.nscount)
        result += "{:04x}".format(self.arcount)
        addr_parts = self.name.split(".")
        for part in addr_parts:
            addr_len = "{:02x}".format(len(part))
            addr_part = binascii.hexlify(part.encode('iso8859-1'))
            result += addr_len
            result += addr_part.decode('iso8859-1')
        result += "00"
        result += "{:04x}".format(self.qtype)
        result += "{:04x}".format(self.qcount)
        return result
