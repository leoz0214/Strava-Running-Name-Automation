"""Main module of the program - entry point."""
import logging
import time

import configure
from const import LOG_FILE


def main() -> None:
    """Main procedure of the program."""
    while True:
        config = configure.get_config()
        

if __name__ == "__main__":
    logging.basicConfig(
        handlers=(logging.FileHandler(LOG_FILE), logging.StreamHandler()),
        encoding="utf8", level=logging.INFO,
        format= "%(asctime)s: %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    main()
