#!/usr/bin/env python3
import argparse
import sys
import logging

from server.config import Config
from server.server import Server


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog=None if not globals().get('__spec__')
        else f'python3 -m {__spec__.name.partition(".")[0]}'
    )

    parser.add_argument('-g', '--get-config',
                        metavar='config_path',
                        help="get config file in given path")
    parser.add_argument('-c', '--config',
                        metavar='config_path',
                        help="run server with given config")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="run server in verbose mode")
    return parser.parse_args()

def main():
    config = Config()
    args_dict = parse_arguments()
    if args_dict.get_config:
        config.unload(args_dict.get_config)
        sys.exit()
    if args_dict.config:
        config.load(args_dict.config)
    log_level = logging.INFO if not args_dict.verbose else logging.DEBUG
    if config.log_file:
        logging.basicConfig(filename=config.log_file,
                            level=log_level,
                            format='[%(asctime)s] - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=log_level,
                            stream=sys.stdout,
                            format='[%(asctime)s] - %(levelname)s - %(message)s')
    logging.info(f'Starting server with {args_dict.config}')
    server = None
    try:
        server = Server(config)
        server.run()
    except KeyboardInterrupt:
        print("Shutting down server...")
    except Exception as e:
        print(e)
        logging.error(e)
    finally:
        if server:
            server.shutdown()
        sys.exit(0 if isinstance(server, Server) else 1)

if __name__ == "__main__":
    main()
