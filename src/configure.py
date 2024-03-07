"""
Module for parsing and building the configuration settings,
including deep validation.
"""
import json
from dataclasses import dataclass

from const import CONFIG_FILE


MIN_REFRESH_MINUTES = 2
MAX_REFRESH_MINUTES = 60
DEFAULT_REFRESH_MINUTES = 5


@dataclass
class Config:
    """All configuration data stored in one data class."""
    client_id: int
    client_secret: str
    refresh_minutes: int


def get_config() -> Config:
    """Loads, validates and returns the configuration data."""
    try:
        with CONFIG_FILE.open("r", encoding="utf8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError("Invalid config JSON file.")
    if not isinstance(data, dict):
        raise TypeError("JSON data must be a dict, not an array.")
    
    try:
        client_id = data["client_id"]
    except KeyError:
        raise ValueError("Client ID not provided.")
    try:
        client_secret = data["client_secret"]
    except KeyError:
        raise ValueError("Client secret not provided.")
    
    refresh_minutes = data.get("refresh_minutes", DEFAULT_REFRESH_MINUTES)
    if (
        not isinstance(refresh_minutes, int)
        or not MIN_REFRESH_MINUTES <= refresh_minutes <= MAX_REFRESH_MINUTES
    ):
        raise ValueError(
            "Refresh minutes must be an integer in the range "
            f"[{MIN_REFRESH_MINUTES}, {MAX_REFRESH_MINUTES}]")

    return Config(client_id, client_secret, refresh_minutes)
