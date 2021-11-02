# DNS-server
Simple DNS-server with iterative dns queries.

## Usage
* Get config for running the server

```sh
python3 -m server -g config.json
```

* Run server with config

```sh
python3 -m server -r config.json
```

| Command | Description |
| --- | --- |
| python3 -m server -h | Show help message |
| python3 -m server -g config_path | Get config file in given path |
| python3 -m server -r config_path | Run server with given config |

## Author

**Artyom Borisov**
