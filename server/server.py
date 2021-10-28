import binascii
import concurrent.futures
import logging
import socket
from functools import reduce

from entities.dns_message import DnsMessage
from entities.flags import Flags
from entities.question import Question
from server.config import Config
from server.timed_lru_cache import TimedLruCache


def get_multiply_response(address: str) -> str:
    return reduce(lambda x, y: int(x) * int(y),
                  address[: address.find('.multiply.')].split('.')) % 256


def parse_request(request: bytes):
    params = list(map(lambda x: x.decode('utf-8'), request.split()))
    return [params[0], bool(int(params[1])), bool(int(params[2]))]


class Server:
    def __init__(self, config: Config):
        self.config = config
        self.cache = TimedLruCache(config.cache_size)
        logging.basicConfig(
            filename=self.config.log_file,
            level=logging.DEBUG,
            format='[%(asctime)s] - %(levelname)s - %(message)s')

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.config.hostname, self.config.port))
            server.listen()
            print(f'Server launched with '
                  f'{self.config.hostname}:{self.config.port}')
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_threads) as executor:
                while True:
                    client, address = server.accept()
                    executor.submit(self.handle_client, client=client)

    def handle_client(self, client: socket) -> None:
        try:
            request = client.recv(4096)
            domain, is_ip6, udp = parse_request(request)
            cache_part = f'{domain} {is_ip6}'
            if cached := self.cache.get_item(cache_part):
                client.sendall(cached.encode('utf-8'))
                response = cached
            elif '.multiply.' in domain:
                multiply_response = str(get_multiply_response(domain))
                response = f'127.0.0.{multiply_response}'
                client.sendall(response.encode('utf-8'))
                self.cache.add_item(cache_part, response, 300)
            else:
                query = get_dns_request(domain, udp, is_ip6)
                if query:
                    response = query.rddata
                    client.sendall(response.encode('utf-8'))
                    self.cache.add_item(cache_part, response, query.ttl)
                else:
                    response = None
            logging.info(f'{domain} - {response}')
        except Exception as e:
            logging.exception(e)
        finally:
            client.close()


def send_dns_message(message, address, port, udp):
    message = message.replace(" ", "").replace("\n", "")
    bytes_message = binascii.unhexlify(message)
    server_address = (address, port)

    if not udp:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_address)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if not udp:
            sock.sendall(bytes_message)
            data = sock.recv(4096)
        else:
            sock.sendto(binascii.unhexlify(message), server_address)
            data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    return binascii.hexlify(data).decode("iso8859-1")[4 if not udp else 0:]


def get_dns_request(domain: str, udp: bool, is_ip6: bool):
    flags = Flags(0, 0, 0, 0, 1, 0, 0, 0)
    type_int = 28 if is_ip6 else 1
    q = Question(1, 0, 0, 0, domain, type_int, 1)
    message = str(DnsMessage(43690, flags, q, []))
    if not udp:
        message = "{:04x}".format(len(message) // 2) + message
    response = send_dns_message(message, "a.root-servers.net", 53, udp)
    result = None
    while response:
        decoded_message = DnsMessage.parse(response)
        ns_url = None
        for query in decoded_message.queries:
            if query.atype == type_int and query.aname == domain:
                result = query
                break
            elif query.atype == 2:
                ns_url = query.rddata
                break
        if not result and ns_url:
            response = send_dns_message(message, ns_url, 53, udp)
        else:
            break
    return result
