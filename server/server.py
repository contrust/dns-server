import binascii
import concurrent.futures
import logging
import socket
import time
from functools import reduce
from threading import Thread
from typing import Optional, Union, List
from dataclasses import astuple

from entities.dns_message import DnsMessage
from entities.query import Query
from entities.question import Question
from entities.flags import Flags
from server.config import Config
from server.timed_lru_cache import TimedLruCache


class Server:
    def __init__(self, config: Config):
        self.config: Config = config
        try:
            self.cache = TimedLruCache.try_load_from_file(config.cache_file,
                                                          config.cache_size)
        except Exception as e:
            logging.error(f'Failed to load cache from file {config.cache_file}: {e}')
            self.cache = TimedLruCache(config.cache_size)
        self.server: Union[socket.socket, None] = None
        self.running: bool = False

    def shutdown(self):
        logging.info('Shutting down server')
        try:
            logging.info(f'Saving cache to file {self.config.cache_file}')
            self.cache.save_to_file(self.config.cache_file)
        except Exception as e:
            logging.error(f'Failed to save cache to file {self.config.cache_file}: {e}')
        finally:
            self.running = False
            if self.server:
                logging.info(f'Closing server {self.server.getsockname()}')
                self.server.close()

    def run(self) -> None:
        self.running = True
        try:
            p1 = Thread(target=self.run_with_udp)
            p2 = Thread(target=self.run_with_tcp)
            p3 = Thread(target=self.update_cache_loop)
            p1.setDaemon(True)
            p2.setDaemon(True)
            p3.setDaemon(True)
            logging.info(f'Server launched on '
                  f'{self.config.hostname}:{self.config.port}')
            p1.start()
            p2.start()
            p3.start()
            p1.join()
            p2.join()
            p3.join()
        except KeyboardInterrupt:
            logging.info('Server stopped by keyboard interrupt')
        except Exception as e:
            logging.error(f'Server crashed: {e}')
        finally:
            self.running = False
            self.shutdown()

    def run_with_udp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.config.hostname, self.config.port))
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.config.max_threads) as executor:
                while self.running:
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
                while self.running:
                    client, address = server.accept()
                    executor.submit(self.handle_tcp_client, client=client, address=address)

    def update_cache_loop(self):
        while self.running:
            self.cache.update()
            time.sleep(1)

    def handle_udp_client(self, server: socket.socket,
                          data: bytes, address: tuple) -> None:
        ip, port = address
        logging.info(f'Handling UDP client {ip}:{port}')
        try:
            response = self.get_bytes_dns_response(data, False)
            if response:
                server.sendto(response, address)
            logging.info(f'Successfully handled UDP client {ip}:{port}')
        except Exception as e:
            logging.error(f'Failed to handle UDP client {ip}:{port}: {e}')

    def handle_tcp_client(self, client: socket.socket, address: tuple) -> None:
        ip, port = address
        logging.info(f'Handling TCP client {ip}:{port}')
        try:
            data = client.recv(8192)
            response = self.get_bytes_dns_response(data, True)
            client.sendall(response)
            logging.info(f'Successfully handled TCP client {ip}:{port}')
        except Exception as e:
            logging.error(f'Failed to handle TCP client {ip}:{port}: {e}')
        finally:
            client.close()

    def get_bytes_dns_response(self, bytes_message: bytes, is_tcp: bool) -> bytes:
        message = get_hexed_string(bytes_message)
        request = DnsMessage.parse(message, is_tcp)
        
        responses: List[DnsMessage] = []
        questions: List[Question] = request.questions
        for question in questions:
            if response := self.get_cached_dns_response(question):
                logging.debug(f'Using cached response for {question.name}')
                responses.append(response)
            else:
                logging.debug(f'Getting response for {question.name}')
                request.questions = [question]
                response = get_dns_response(request,
                                            self.config.proxy_hostname,
                                            self.config.proxy_port,
                                            is_tcp)
                if not response:
                    request.flags.qr = 1
                    request.flags.reply_code = 2
                    return binascii.unhexlify(str(request))
                logging.debug(f'Caching response for {question.name}')
                self.cache_dns_response(question, response)
                responses.append(response)
        answers = set()
        authorities = set()
        add_records = set()
        for response in responses:
            answers |= set(response.answers)
            authorities |= set(response.authorities)
            add_records |= set(response.add_records)
        response = DnsMessage(is_tcp, request.transaction_id, 
                            Flags(1, 0, 0, 0, 0, 0, 0, 0),
                            request.questions,
                            list(answers),
                            list(authorities),
                            list(add_records))
        return binascii.unhexlify(str(response))

    def get_cached_dns_response(self, question: Question) -> Optional[DnsMessage]:
        item = question.to_tuple()
        return self.cache.get_item(item)

    def cache_dns_response(self, question: Question, response: DnsMessage) -> None:
        queries = response.get_all_queries()
        if len(queries) == 0:
            return
        min_ttl = min(query.ttl for query in queries)
        item = question.to_tuple()
        self.cache.add_item(item, response, min_ttl)

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
            logging.error(f'Failed to connect to {address}:{port}: {e}')
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
        logging.error(f'Failed to send/receive data to/from {address}:{port}: {e}')
    finally:
        sock.close()
    return get_hexed_string(data)


def get_dns_response(request, hostname, port, tcp: bool) -> Optional[DnsMessage]:
    if request is None:
        return None
    if len(request.questions) == 0:
        return None
    domain = request.questions[0].name
    question_type = request.questions[0].tp
    data = str(request)
    try:
        string_response = get_dns_string_response_from_socket(data,
                                                              hostname,
                                                              port, tcp)
    except Exception as e:
        logging.error(f'Failed to get DNS response from {hostname}:{port}: {e}')
        return None
    while string_response:
        try:
            response = DnsMessage.parse(string_response, tcp)
        except Exception as e:
            logging.error(f'Failed to parse DNS response: {e}')
            return None
        for answer in response.answers:
            if answer.tp == question_type and answer.name == domain:
                return response
        for authority in response.authorities:
            if authority.tp == 2 and authority.name != "":
                address = authority.data
                for record in response.add_records:
                    if record.name == address and record.tp == 1:
                        address = record.data
                        break
                try:
                    string_response = get_dns_string_response_from_socket(
                        data, address, 53, tcp)
                except Exception as e:
                    logging.error(f'Failed to get DNS response from {address}:53: {e}')
                    continue
                if not string_response:
                    continue
                break
        else:
            return response
    return None


def get_hexed_string(data: bytes) -> str:
    return binascii.hexlify(data).decode("iso8859-1")
