.PHONY: install run test clean config

# Default Python interpreter
PYTHON = python3

# Default configuration file
CONFIG = config.json

config:
	sudo $(PYTHON) -m server -g $(CONFIG)

run:
	sudo $(PYTHON) -m server -c $(CONFIG)

run-verbose:
	sudo $(PYTHON) -m server -c $(CONFIG) -v

test:
	$(PYTHON) -m unittest tests/test_timed_lru_cache.py -v

clean:
	rm -f *.pyc
	rm -f server/*.pyc
	rm -f entities/*.pyc
	rm -f tests/*.pyc
	rm -f __pycache__/*
	rm -f server/__pycache__/*
	rm -f entities/__pycache__/*
	rm -f tests/__pycache__/*
	rm -f *.log
	rm -f *.pkl

help:
	@echo "Available commands:"
	@echo "  make config      - Generate default configuration file"
	@echo "  make run         - Run the DNS server"
	@echo "  make run-verbose - Run the DNS server with verbose logging"
	@echo "  make test        - Run unit tests"
	@echo "  make clean       - Clean up Python cache files and logs"
	@echo "  make help        - Show this help message"