"""Run this script to start up the main program."""
import pathlib
import sys


SRC_FOLDER = pathlib.Path(__file__).parent / "src"
sys.path.append(str(SRC_FOLDER))

from src import main


if __name__ == "__main__":
    main.main()
