"""Useful runtime constants that can be used throughout the program."""
import pathlib


DATA_FOLDER = pathlib.Path(__file__).parent.parent / "data"
CONFIG_FILE = DATA_FOLDER / "config.json"
LOG_FILE = DATA_FOLDER / "log.log"
CREDENTIALS_FILE = DATA_FOLDER / "_credentials.json"
