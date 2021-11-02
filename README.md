# DNS-server
Simple DNS-server which iteratively gets domain's public ip.

## Usage
* Get config for running the server

```sh
sudo python3 -m server -g config.json
```

* Run server with config

```sh
sudo python3 -m server -r config.json
```

| Command | Description |
| --- | --- |
| python3 -m server -h | Show help message |
| python3 -m server -g config_path | Get config file in given path |
| python3 -m server -r config_path | Run server with given config |

## Features

- Handling multiple clients on server with multithreading
- Caching responses based on ttl
- TCP and UDP requests handling
- Several types of records are available: A and AAAA
- If the request contains ".multiply.", then server responds with IP 127.0.0.X, where
       X - product of numbers up to "multiply" modulo 256
## Author

**Artyom Borisov**
