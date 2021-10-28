from dataclasses import dataclass


@dataclass
class Query:
    def __init__(self, qdcount: int, ancount: int, nscount: int, arcount: int,
                 aname: str, atype: int, aclass: int, ttl: int, rddata: str):
        self.qcount = qdcount
        self.ancount = ancount
        self.nscount = nscount
        self.arcount = arcount
        self.aname = aname
        self.atype = atype
        self.aclass = aclass
        self.ttl = ttl
        self.rddata = rddata
