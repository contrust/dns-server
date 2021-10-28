import socket


def get_dns_server_response(domain, server, port, udp, is_ip6):
    s = socket.create_connection((server, port))
    s.sendall(b' '.join(map(lambda x: str(x).encode('utf-8'),
                            [domain, str(int(is_ip6)), str(int(udp))])))
    response = s.recv(4096)
    str_response = response.decode('utf-8')
    return str_response
