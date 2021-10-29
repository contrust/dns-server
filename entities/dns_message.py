import binascii
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address

from entities.flags import Flags
from entities.query import Query
from entities.question import Question


@dataclass
class DnsMessage:
    def __init__(self, transaction_id: int,
                 flags: Flags,
                 questions: list[Question],
                 answers: list[Query],
                 authorities: list[Query],
                 add_records: list[Query]):
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
        return result

    @staticmethod
    def parse(message: str):
        message_transaction_id = int(message[0:4], 16)
        message_flags = Flags.parse(message[4:8])
        qdcount = int(message[8:12], 16)
        ancount = int(message[12:16], 16)
        nscount = int(message[16:20], 16)
        arcount = int(message[20:24], 16)
        questions, answers, authorities, add_records = [], [], [], []
        start = 24
        for _ in range(qdcount):
            question_parts = get_name_partition(message, start, [])
            type_start = start + (
                len("".join(question_parts))) + (len(question_parts) * 2) + 2
            question = Question(".".join(
                map(lambda p: binascii.unhexlify(p).decode('iso8859-1'),
                    question_parts)),
                int(message[type_start: type_start + 4], 16),
                int(message[type_start + 4: type_start + 8], 16))
            questions.append(question)
            start = type_start + 8
        for i in range(sum([ancount, nscount, arcount])):
            if start >= len(message):
                break
            name_len = (4 if message[start] == "c"
                        else message[start:].find("00") + 2)
            name = decompress_name(message[start: start + name_len], message)
            tp = int(message[start + name_len: start + name_len + 4], 16)
            cls = int(message[start + name_len + 4: start + name_len + 8], 16)
            ttl = int(message[start + name_len + 8: start + name_len + 16], 16)
            length = int(message[start + name_len + 16: start + name_len + 20],
                         16)
            address = message[start + name_len + 20:
                              start + name_len + 20 + length * 2]
            start = start + name_len + 20 + length * 2
            if tp == 1:
                decoded_address = str(IPv4Address(int(address, 16)))
            elif tp in {2, 5}:
                decoded_address = decompress_name(address, message)
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
        dns_message = DnsMessage(message_transaction_id, message_flags,
                                 questions, answers, authorities, add_records)
        return dns_message


def decompress_name(name: str, message: str):
    return ".".join(
        map(lambda p: binascii.unhexlify(p).decode('iso8859-1'),
            get_name_partition(decompress_message(name, message), 0, [])))


def get_name_partition(name, start, parts):
    part_start = start + 2
    len_octet = name[start: part_start]
    if not len_octet:
        return parts
    part_end = part_start + (int(len_octet, 16) * 2)
    parts.append(name[part_start:part_end])
    if (name[part_end: part_end + 2] == "00" or
            part_end > len(name)):
        return parts
    else:
        return get_name_partition(
            name, part_end, parts)


def decompress_message(msg_substring, msg):
    if len(msg_substring) >= 4 and msg_substring[-4] == "c":
        msg_substring = (msg_substring[:-4] +
                         decompress_four_bytes(msg_substring[-4:], msg))
    return msg_substring


def decompress_four_bytes(four_bytes: str, message: str) -> str:
    if len(four_bytes) != 4:
        return four_bytes
    start = int(four_bytes[-3:], 16) * 2
    end = start
    for i in range(1, (len(message) - start) // 2 + 1):
        if message[start + i * 2: start + i * 2 + 2] == "00":
            end = start + i * 2
            break
        if message[start + i * 2] == "c":
            end = start + i * 2 + 4
            break
    result = message[start: end]
    if result[-4] == "c":
        result = (message[start: end - 4] +
                  decompress_four_bytes(message[end - 4: end], message))
    return result
