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
            print(f'Server launched on '
                  f'{self.config.hostname}:{self.config.port}')
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_threads) as executor:
                while True:
                    client, address = server.accept()
                    executor.submit(self.handle_client, client=client)

    def handle_client(self, client: socket) -> None:
        try:
            request = client.recv(4096)
            domain, is_ip6, tcp = parse_request(request)
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
                query = get_dns_request(domain, tcp, is_ip6)
                if query:
                    response = query.data
                    client.sendall(response.encode('utf-8'))
                    self.cache.add_item(cache_part, response, query.ttl)
                else:
                    response = None
            logging.info(f'{domain} - {response}')
        except Exception as e:
            logging.exception(e)
        finally:
            client.close()


def send_dns_message(message, address, port, tcp):
    message = message.replace(" ", "").replace("\n", "").strip()
    bytes_message = binascii.unhexlify(message)
    server_address = (address, port)
    if tcp:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_address)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    try:
        if tcp:
            sock.sendall(bytes_message)
            data = sock.recv(4096)
        else:
            sock.sendto(binascii.unhexlify(message), server_address)
            data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    return binascii.hexlify(data).decode("iso8859-1")[4 if tcp else 0:]


def get_dns_request(domain: str, tcp: bool, is_ip6: bool):
    flags = Flags(0, 0, 0, 0, 1, 0, 0, 0)
    type_int = 28 if is_ip6 else 1
    q = Question(domain, type_int, 1)
    message = str(DnsMessage(43690, flags, [q], [], [], []))
    if tcp:
        message = "{:04x}".format(len(message) // 2) + message
    response = send_dns_message(message, "a.root-servers.net", 53, tcp)
    while response:
        decoded_message = DnsMessage.parse(response)
        for answer in decoded_message.answers:
            if answer.tp == type_int and answer.name == domain:
                return answer
            elif answer.tp == 5 and answer.name == domain:
                return get_dns_request(answer.data, tcp, is_ip6)
        for authority in decoded_message.authorities:
            if authority.tp == 2 and authority.name != "":
                address = authority.data
                for record in decoded_message.add_records:
                    if record.name == address and record.tp == 1:
                        address = record.data
                        break
                response = send_dns_message(message, address, 53, tcp)
                break
        else:
            break
    return None
