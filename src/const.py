"""Useful runtime constants that can be used throughout the program."""
import pathlib


FOLDER = pathlib.Path(__file__).parent.parent
DATA_FOLDER = FOLDER / "data"
CONFIG_FILE = DATA_FOLDER / "config.json"
LOG_FILE = DATA_FOLDER / "log.log"
CREDENTIALS_FILE = DATA_FOLDER / "_credentials.json"
SEEN_ACTIVITIES_FILE = DATA_FOLDER / "_seen_activities.txt"
# BBC Weather data database. This will change depending
# depending the location of the DB.
# At least this is better than hard-coding the absolute path...
# CONTEXT OF MY USAGE ONLY - NOT GENERALISED.
import platform
if platform.system() == "Windows":
    WEATHER_FOLDER = FOLDER.parent / "WeatherAutomation"
else:
    WEATHER_FOLDER = FOLDER.parent / "weather_automate"
WEATHER_DB_FILE = WEATHER_FOLDER / "data" / "database.db"

BIN_FOLDER = FOLDER / "bin"
GEO_DLL_FILE = BIN_FOLDER / "geo.dll"
GEO_SO_FILE = BIN_FOLDER / "geo.so"
