# DNS-server
Simple DNS-server with iterative dns queries.

## Usage
Firstly, you need to run DNS-server with config.
* Get config

```sh
python3 -m server -g config.json
```

* Run server with config

```sh
python3 -m server -r config.json
```
Then, you can send request to the server via client.
* Example of getting ip6 address of google.com via udp protocol

```sh
python3 -m client -d google.com -u -ip6
```
## Server

| Command | Description |
| --- | --- |
| python3 -m server -h | Show help message |
| python3 -m server -g config_path | Get config file in given path |
| python3 -m server -r config_path | Run server with given config |

## Client
| Command | Description |
| --- | --- |
| python3 -m client -h  | Show help message  |
| python3 -m client -d domain | Get public ip of given domain |
* Optional arguments

| Argument | Description |
| --- | --- |
| -s hostname | Dns server hostname, localhost by default |
| -p port | Port of dns server, 2021 by default |
| -u |  Use udp protocol, tcp by default |
| -ip6 |  Get ip6 address, ip4 by default |

## Author

**Artyom Borisov**

* Github: [@contrust](https://github.com/contrust)

