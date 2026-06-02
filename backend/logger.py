import logging
from logging.config import dictConfig
import yaml
import os

_configured = False

def setup_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        if not os.path.exists("log/"):
            os.makedirs("log/")
        try:
            with open("logger.yaml", "r") as f:
                config = yaml.safe_load(f)
                dictConfig(config)
                _configured = True
        except FileNotFoundError:
            print("Logging configuration file not found. Exiting...")
            exit(1)
    return logging.getLogger(name)