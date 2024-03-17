"""Utility functions for the program."""
import math


EARTH_RADIUS = 6378.137


def haversine_distance(
    lat1: float, long1: float, lat2: float, long2: float
) -> float:
    """Haversine distance between two lat/long points in km."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(long2 - long1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = (
        math.sin(dlat / 2)**2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2)
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS * c


def hhmm_to_minutes(hhmm: str) -> int:
    """Converts HHMM to minutes since 0000."""
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def seconds_to_mmss(seconds: float) -> str:
    """Converts seconds to MM:SS"""
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    return f"{str(minutes).zfill(2)}:{str(seconds).zfill(2)}"


def seconds_to_hhmmss(seconds: float) -> str:
    """Converts seconds to HH:MM:SS"""
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return ":".join(str(part).zfill(2) for part in (hours, minutes, seconds))
