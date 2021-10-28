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
                 question: Question,
                 queries: list[Query]):
        self.transaction_id = transaction_id
        self.flags = flags
        self.question = question
        self.queries = queries

    def __str__(self):
        message = ""
        message += "{:04x}".format(self.transaction_id)
        message += str(self.flags)
        message += str(self.question)
        return message

    @staticmethod
    def parse(message: str):
        message_transaction_id = int(message[0:4], 16)
        message_flags = Flags.parse(message[4:8])
        qdcount = int(message[8:12], 16)
        ancount = int(message[12:16], 16)
        nscount = int(message[16:20], 16)
        arcount = int(message[20:24], 16)
        question_start = 24
        question_parts = get_address_partition_from_decompressed_address(
            message, question_start, [])

        question_type_start = question_start + (
            len("".join(question_parts))) + (len(question_parts) * 2) + 2
        question_class_start = question_type_start + 4

        message_question = Question(qdcount, ancount, nscount, arcount,
                                    ".".join(
                                        map(lambda p: binascii.unhexlify(
                                            p).decode('utf-8'),
                                            question_parts)),
                                    int(message[
                                        question_type_start:
                                        question_class_start],
                                        16),
                                    int(message[
                                        question_class_start:
                                        question_class_start + 4],
                                        16))
        start = question_class_start + 4
        queries = []
        while start < len(message):
            name_len = 4 if message[start] == "c" else message[start:].find("00") + 2
            aname = get_decompressed_ns_address(
                message[start: start + name_len], message)
            atype = int(message[start + name_len:start + name_len + 4],
                        16)
            aclass = int(
                message[start + name_len + 4:start + name_len + 8], 16)
            ttl = int(
                message[start + name_len + 8:start + name_len + 16], 16)
            length = int(message[start + name_len + 16: start + name_len + 20], 16)
            address = message[start + name_len + 20:
                              start + name_len + 20 + length * 2]
            start = start + name_len + 20 + length * 2
            if atype == 1:
                decoded_address = str(IPv4Address(int(address, 16)))
            elif atype == 2:
                decoded_address = get_decompressed_ns_address(address,
                                                              message)
            elif atype == 28:
                decoded_address = str(IPv6Address(int(address, 16)))
            else:
                continue
            query = Query(qdcount, ancount,
                          nscount, arcount,
                          aname, atype, aclass, ttl,
                          decoded_address)
            queries.append(query)
        dns_message = DnsMessage(message_transaction_id, message_flags,
                          message_question, queries)
        return dns_message


def get_type_id(str_type):
    types = [
        "ERROR",
        "A",
        "NS",
        "MD",
        "MF",
        "CNAME",
        "SOA",
        "MB",
        "MG",
        "MR",
        "NULL",
        "WKS",
        "PTS",
        "HINFO",
        "MINFO",
        "MX",
        "TXT"
    ]
    return (types.index(str_type) if isinstance(str_type, str) else
            "A" if str_type == 1 else
            "NS" if str_type == 2 else
            "AAAA" if str_type == 28 else "Unknown")


def get_decompressed_ns_address(dns_compressed_address: str, message: str):
    return ".".join(
        map(lambda p: binascii.unhexlify(p).decode('utf-8'),
            get_address_partition_from_decompressed_address(
                decompress_message(dns_compressed_address, message), 0, [])))


def get_address_partition_from_decompressed_address(decompressed_address,
                                                    start, parts):
    part_start = start + 2
    len_octet = decompressed_address[start: part_start]
    if not len_octet:
        return parts
    part_end = part_start + (int(len_octet, 16) * 2)
    parts.append(decompressed_address[part_start:part_end])
    if (decompressed_address[part_end: part_end + 2] == "00" or
            part_end > len(decompressed_address)):
        return parts
    else:
        return get_address_partition_from_decompressed_address(
            decompressed_address, part_end, parts)


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
