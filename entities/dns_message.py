import binascii
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address

from entities.flags import Flags
from entities.query import Query
from entities.question import Question


@dataclass
class DnsMessage:
    def __init__(self, is_tcp: bool,
                 transaction_id: int,
                 flags: Flags,
                 questions: list[Question],
                 answers: list[Query],
                 authorities: list[Query],
                 add_records: list[Query]):
        self.is_tcp = is_tcp
        self.transaction_id = transaction_id
        self.flags = flags
        self.questions = questions
        self.answers = answers
        self.authorities = authorities
        self.add_records = add_records

    def __str__(self):
        result = ""
        result += "{:04x}".format(self.transaction_id)
        result += str(self.flags)
        result += "{:04x}".format(len(self.questions))
        result += "{:04x}".format(len(self.answers))
        result += "{:04x}".format(len(self.authorities))
        result += "{:04x}".format(len(self.add_records))
        for question in self.questions:
            result += str(question)
        for query in self.answers + self.authorities + self.add_records:
            result += str(query)
        if self.is_tcp:
            result = "{:04x}".format(len(result) // 2) + result
        return result

    @staticmethod
    def parse(message: str, is_tcp: bool):
        if is_tcp:
            message = message[4:]
        message_transaction_id = int(message[0:4], 16)
        message_flags = Flags.parse(message[4:8])
        qdcount = int(message[8:12], 16)
        ancount = int(message[12:16], 16)
        nscount = int(message[16:20], 16)
        arcount = int(message[20:24], 16)
        questions, answers, authorities, add_records = [], [], [], []
        start = 24
        for _ in range(qdcount):
            name_end = find_name_end_index(start, message)
            question = Question(
                get_joined_by_dots_name(message[start: name_end], message),
                int(message[name_end: name_end + 4], 16),
                int(message[name_end + 4: name_end + 8], 16))
            questions.append(question)
            start = name_end + 8
        for i in range(sum([ancount, nscount, arcount])):
            if start >= len(message):
                break
            end = find_name_end_index(start, message)
            name = get_joined_by_dots_name(message[start: end], message)
            tp = int(message[end: end + 4], 16)
            cls = int(message[end + 4: end + 8], 16)
            ttl = int(message[end + 8: end + 16], 16)
            length = int(message[end + 16: end + 20],
                         16)
            address = message[end + 20:
                              end + 20 + length * 2]
            start = end + 20 + length * 2
            if tp == 1:
                decoded_address = str(IPv4Address(int(address, 16)))
            elif tp in {2, 12}:
                decoded_address = get_joined_by_dots_name(address, message)
            elif tp == 28:
                decoded_address = str(IPv6Address(int(address, 16)))
            else:
                continue
            query = Query(name, tp, cls, ttl, decoded_address)
            if 0 <= i < ancount:
                answers.append(query)
            if ancount <= i < ancount + nscount:
                authorities.append(query)
            else:
                add_records.append(query)
        dns_message = DnsMessage(is_tcp, message_transaction_id, message_flags,
                                 questions, answers, authorities, add_records)
        return dns_message

    def get_all_queries(self):
        return self.answers + self.authorities + self.add_records


def get_joined_by_dots_name(name: str, message: str):
    return ".".join(
        map(lambda p: binascii.unhexlify(p).decode('iso8859-1'),
            get_name_partition(decompress_message(name, message), 0, [])))


def get_name_partition(name, start, parts):
    len_octet = name[start: start + 2]
    if not len_octet:
        return parts
    part_end = start + 2 + int(len_octet, 16) * 2
    parts.append(name[start + 2: part_end])
    if part_end > len(name) or name[part_end: part_end + 2] == "00":
        return parts
    else:
        return get_name_partition(name, part_end, parts)


def decompress_message(msg_substring, msg):
    if len(msg_substring) >= 4 and msg_substring[-4] == "c":
        msg_substring = (msg_substring[:-4] +
                         decompress_four_bytes(msg_substring[-4:], msg))
    return msg_substring


def decompress_four_bytes(four_bytes: str, message: str) -> str:
    if len(four_bytes) != 4:
        return four_bytes
    start = int(four_bytes[-3:], 16) * 2
    end = find_name_end_index(start, message)
    result = message[start: end]
    if result[-4] == "c":
        result = (message[start: end - 4] +
                  decompress_four_bytes(message[end - 4: end], message))
    return result


def find_name_end_index(start, message):
    end = start
    for i in range(0, (len(message) - start) // 2):
        if message[start + i * 2: start + i * 2 + 2] == "00":
            end = start + i * 2 + 2
            break
        if message[start + i * 2] == "c":
            end = start + i * 2 + 4
            break
    return end
