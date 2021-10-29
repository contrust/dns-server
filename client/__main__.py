#!/usr/bin/env python3
import argparse

from client.client import get_dns_server_response


def parse_arguments():
    """
    Parse console arguments.
    """
    parser = argparse.ArgumentParser(
        prog=None if not globals().get('__spec__')
        else f'python3 -m {__spec__.name.partition(".")[0]}'
    )
    parser.add_argument('-d', '--domain',
                        metavar='domain',
                        required=True,
                        help='domain to get public ip')
    parser.add_argument('-s', '--server',
                        metavar='hostname',
                        required=False,
                        help='dns server hostname, localhost by default')
    parser.add_argument('-p', '--port',
                        metavar='port',
                        required=False,
                        help='port of dns server, 2021 by default')
    parser.add_argument('-t', '--tcp',
                        required=False,
                        action='store_true',
                        help='use tcp protocol, udp by default')
    parser.add_argument('-ip6',
                        required=False,
                        action='store_true',
                        help='get ip6 address, ip4 by default')
    return parser.parse_args()


def main():
    args_dict = vars(parse_arguments())
    domain = args_dict['domain']
    dns_server = args_dict['server'] if args_dict['server'] else 'localhost'
    port = int(args_dict['port']) if args_dict['port'] else 2021
    udp = True if args_dict['tcp'] else False
    is_ip6 = True if args_dict['ip6'] else False
    server_response = get_dns_server_response(domain, dns_server, port, udp,
                                              is_ip6)
    print(server_response)


if __name__ == '__main__':
    main()
