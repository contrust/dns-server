import binascii
import concurrent.futures
import logging
import socket
from functools import reduce
from threading import Thread
from typing import Optional

from entities.dns_message import DnsMessage
from entities.query import Query
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
            p1 = Thread(target=self.run_with_udp)
            p2 = Thread(target=self.run_with_tcp)
            p1.setDaemon(True)
            p2.setDaemon(True)
            print(f'Server launched on '
                  f'{self.config.hostname}:{self.config.port}')
            p1.start()
            p2.start()
            p1.join()
            p2.join()
        except KeyboardInterrupt:
            pass
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
                          data: bytes, address: tuple) -> None:
        try:
            response = self.get_bytes_dns_response(data, False)
            server.sendto(response, address)
        except Exception as e:
            logging.error(e)

    def handle_tcp_client(self, client: socket.socket) -> None:
        try:
            data = client.recv(8192)
            response = self.get_bytes_dns_response(data, True)
            client.sendall(response)
        except Exception as e:
            logging.error(e)
        finally:
            client.close()

    def get_bytes_dns_response(self, bytes_message: bytes, is_tcp: bool) \
            -> bytes:
        message = get_hexed_string(bytes_message)
        request = DnsMessage.parse(message, is_tcp)
        cache_part = tuple([request.questions[0].name,
                            request.questions[0].tp, is_tcp])
        if cached := self.cache.get_item(cache_part):
            cached.transaction_id = request.transaction_id
            return binascii.unhexlify(str(cached))
        elif '.multiply.' in request.questions[0].name:
            multiply_response = get_multiply_response(request.questions[0].name)
            address = f'127.0.0.{multiply_response}'
            request.flags.qr = 1
            request.answers.append(Query(request.questions[0].name,
                                         1, 1, 300, address))
            self.cache.add_item(cache_part, request, 300)
            return binascii.unhexlify(str(request))
        else:
            response = get_dns_response(request, is_tcp)
            if response:
                response.add_records = []
                response.authorities = []
            else:
                request.flags.qr = 1
                response = request
            self.cache.add_item(cache_part, response,
                                response.answers[-1].ttl
                                if len(response.answers) else 300)
            return binascii.unhexlify(str(response))


def get_dns_string_response_from_socket(hexed_message: str,
                                        address: str,
                                        port: int,
                                        tcp: bool) -> str:
    hexed_message = hexed_message.replace(" ", "").replace("\n", "").strip()
    bytes_message = binascii.unhexlify(hexed_message)
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
            sock.sendto(binascii.unhexlify(hexed_message), server_address)
            data, _ = sock.recvfrom(4096)
    except socket.error as e:
        logging.error(e)
    finally:
        sock.close()
    return get_hexed_string(data)


def get_dns_response(request: DnsMessage, tcp: bool) -> Optional[DnsMessage]:
    domain = request.questions[0].name
    question_type = request.questions[0].tp
    data = str(request)
    string_response = get_dns_string_response_from_socket(data,
                                                          "a.root-servers.net",
                                                          53, tcp)
    while string_response:
        response = DnsMessage.parse(string_response, tcp)
        for answer in response.answers:
            if answer.tp == question_type and answer.name == domain:
                return response
            elif answer.tp == 5 and answer.name == domain:
                request.questions[0].name = answer.data
                result = get_dns_response(request, tcp)
                if not result:
                    request.flags.qr = 1
                    result = request
                result.questions[0].name = domain
                result.answers = [answer] + result.answers
                return result
        for authority in response.authorities:
            if authority.tp == 2 and authority.name != "":
                address = authority.data
                for record in response.add_records:
                    if record.name == address and record.tp == 1:
                        address = record.data
                        break
                string_response = get_dns_string_response_from_socket(
                    data, address, 53, tcp)
                if not string_response:
                    continue
                break
        else:
            break
    return None


def get_hexed_string(data: bytes) -> str:
    return binascii.hexlify(data).decode("iso8859-1")
