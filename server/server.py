import binascii
import concurrent.futures
import logging
import socket
import sys
import traceback
from functools import reduce
from multiprocessing import Process
from pprint import pprint

from entities.dns_message import DnsMessage
from entities.flags import Flags
from entities.query import Query
from entities.question import Question
from server.config import Config
from server.timed_lru_cache import TimedLruCache


def get_multiply_response(address: str) -> int:
    numbers = [int(x) for x in address[: address.find('.multiply.')].split('.')
               if x.isnumeric()]
    if len(numbers) == 0:
        return 0
    if len(numbers) == 1:
        return numbers[0] % 256
    else:
        return reduce(lambda x, y: x * y, numbers) % 256


def parse_request(request: bytes):
    params = list(map(lambda x: x.decode('utf-8'), request.split()))
    return [params[0], bool(int(params[1])), bool(int(params[2]))]


class Server:
    def __init__(self, config: Config):
        self.config = config
        self.cache = TimedLruCache(config.cache_size)
        self.server = None
        logging.basicConfig(
            filename=self.config.log_file,
            level=logging.DEBUG,
            format='[%(asctime)s] - %(levelname)s - %(message)s')

    def run(self) -> None:
        try:
            p1 = Process(target=self.run_with_udp)
            p2 = Process(target=self.run_with_tcp)
            p1.start()
            p2.start()
            print(f'Server launched on '
                  f'{self.config.hostname}:{self.config.port}')
        except Exception as e:
            logging.error(e)

    def run_with_udp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.config.hostname, self.config.port))
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_threads) as executor:
                while True:
                    data, address = server.recvfrom(8192)
                    executor.submit(self.handle_udp_client,
                                    server=server, data=data, address=address)

    def run_with_tcp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.config.hostname, self.config.port))
            server.listen()
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_threads) as executor:
                while True:
                    client, address = server.accept()
                    executor.submit(self.handle_tcp_client, client=client)

    def handle_udp_client(self, server: socket.socket,
                          data: bytes, address: tuple):
        try:
            response = self.get_dns_response(data, False)
            server.sendto(response, address)
        except Exception as e:
            traceback.print_exc()
            logging.error(e)

    def handle_tcp_client(self, client: socket.socket):
        try:
            data = client.recv(8192)
            response = self.get_dns_response(data, True)
            client.sendall(response)
        except Exception as e:
            logging.error(e)
        finally:
            client.close()

    def get_dns_response(self, data: bytes, tcp: bool) -> bytes:
        message = binascii.hexlify(data).decode("iso8859-1")
        message = message[4:] if tcp else message
        m = DnsMessage.parse(message)
        cache_part = tuple([m.questions[0].name, m.questions[0].tp, tcp])
        if cached := self.cache.get_item(cache_part):
            cached.transaction_id = m.transaction_id
            result = str(cached)
            if tcp:
                result = "{:04x}".format(len(result) // 2) + result
            result = binascii.unhexlify(result)
            return result
        elif '.multiply.' in m.questions[0].name:
            multiply_response = get_multiply_response(m.questions[0].name)
            address = f'127.0.0.{multiply_response}'
            m.flags.qr = 1
            m.answers.append(Query(m.questions[0].name, 1, 1, 300, address))
            self.cache.add_item(cache_part, m, 300)
            result = str(m)
            if tcp:
                result = "{:04x}".format(len(result) // 2) + result
            result = binascii.unhexlify(result)
            return result
        else:
            res = get_dns_request(m, tcp)
            if res:
                res.add_records = []
                res.authorities = []
            else:
                m.flags.qr = 1
                res = m
            result = str(res)
            if tcp:
                result = "{:04x}".format(len(result) // 2) + result
            result = binascii.unhexlify(result)
            self.cache.add_item(cache_part, res,
                                res.answers[0].ttl if len(res.answers)
                                else 300)
            return result

def send_dns_message(msg, address, port, tcp):
    msg = msg.replace(" ", "").replace("\n", "").strip()
    bytes_message = binascii.unhexlify(msg)
    server_address = (address, port)
    sock = (socket.socket(socket.AF_INET, socket.SOCK_STREAM) if tcp
            else socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
    sock.settimeout(1)
    if tcp:
        try:
            sock.connect(server_address)
        except socket.error as e:
            logging.error(e)
            return ''
    data = b''
    try:
        if tcp:
            sock.sendall(bytes_message)
            data = sock.recv(4096)
        else:
            sock.sendto(binascii.unhexlify(msg), server_address)
            data, _ = sock.recvfrom(4096)
    except socket.error as e:
        logging.error(e)
    finally:
        sock.close()
    return binascii.hexlify(data).decode("iso8859-1")[4 if tcp else 0:]


def get_dns_request(message: DnsMessage, tcp: bool):
    domain = message.questions[0].name
    type_int = message.questions[0].tp
    data = str(message)
    if tcp:
        data = "{:04x}".format(len(data) // 2) + data
    response = send_dns_message(data, "a.root-servers.net", 53, tcp)
    while response:
        decoded_message = DnsMessage.parse(response)
        for answer in decoded_message.answers:
            if answer.tp == type_int and answer.name == domain:
                return decoded_message
            elif answer.tp == 5 and answer.name == domain:
                message.questions[0].name = answer.data
                result = get_dns_request(message, tcp)
                result.questions[0].name = domain
                result.answers = [answer] + result.answers
                return result
        for authority in decoded_message.authorities:
            if authority.tp == 2 and authority.name != "":
                address = authority.data
                for record in decoded_message.add_records:
                    if record.name == address and record.tp == 1:
                        address = record.data
                        break
                response = send_dns_message(data, address, 53, tcp)
                if not response:
                    continue
                break
        else:
            break
    return None
