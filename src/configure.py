"""
Module for parsing and building the configuration settings,
including deep validation.
"""
import itertools
import json
import numbers
import string
from dataclasses import dataclass

from const import CONFIG_FILE


# Sensible ranges/defaults.
MIN_REFRESH_MINUTES = 2
MAX_REFRESH_MINUTES = 60
DEFAULT_REFRESH_MINUTES = 5
MIN_HEART_RATE = 50
MAX_HEART_RATE = 250


@dataclass
class Config:
    """All configuration data stored in one data class."""
    client_id: int
    client_secret: str
    refresh_minutes: int


def validate_client_id(client_id: int) -> None:
    """Checks the client ID is a sensible integer."""
    if isinstance(client_id, str) and client_id.isdigit():
        client_id = int(client_id)
    if not isinstance(client_id, int):
        raise TypeError("Client ID must be an integer.")
    if client_id < 0:
        raise ValueError("Invalid client ID.")


def validate_client_secret(client_secret: str) -> None:
    """Checks the client secret is a valid lowercase hex string."""
    if not isinstance(client_secret, str):
        raise TypeError("Client secret must be a string.")
    if not client_secret:
        raise ValueError("Client secret must not be empty.")
    if any(char not in string.hexdigits for char in client_secret):
        raise ValueError("Client secret must be hexadecimal.")
    if not client_secret.islower():
        raise ValueError(
            "Client secret is case-sensitive and must be fully lowercase.")


def validate_refresh_minutes(refresh_minutes: int) -> None:
    """Ensures the refresh minutes is an in-range integer."""
    if not isinstance(refresh_minutes, int):
        raise TypeError("Refresh minutes must be an integer.")
    if not MIN_REFRESH_MINUTES <= refresh_minutes <= MAX_REFRESH_MINUTES:
        raise ValueError(
            "Refresh minutes must be in the range "
            f"[{MIN_REFRESH_MINUTES}, {MAX_REFRESH_MINUTES}]")


def validate_heart_rate_zones(heart_rate_zones: dict[str, int]) -> None:
    """Ensure HR zones are 1-5, with ascending HR thresholds."""
    if not isinstance(heart_rate_zones, dict):
        raise TypeError("Heart rate zones must be a dictionary.")
    thresholds = [None] * 5
    for zone, threshold in heart_rate_zones.items():
        if zone not in ("1", "2", "3", "4", "5"):
            raise ValueError("Heart rate zones must be from 1 to 5 only.")
        if not isinstance(threshold, int):
            raise TypeError("Heart rates must be integers.")
        if not MIN_HEART_RATE <= threshold <= MAX_HEART_RATE:
            raise TypeError("Heart rates must be sensible values.")
        thresholds[int(zone) - 1] = threshold
    if None in thresholds:
        raise ValueError("All heart rate zones from 1 to 5 must be provided.")
    if not all(hr1 < hr2 for hr1, hr2 in itertools.pairwise(thresholds)):
        raise ValueError(
            "Heart rate thresholds must increase for increasing zones.")
    

def valid_marker_key(key: str) -> bool:
    """
    Returns True if a key is suitable as a marker
    - alphanumeric and underscores only. Allow all underscores.
    """
    # If underscores removed and string becomes empty,
    # default to "a", returning True.
    return key and (key.replace("_", "") or "a").isalnum()


def validate_title(title: str | list[str] | None, metric: str) -> None:
    """
    Validates a title or titles, raising an error if invalid.
    Accepted: None, string, list of strings
    """
    if (
        title is not None and not isinstance(title, str)
        and not (
            isinstance(title, list) and title
            and all(isinstance(option, str) for option in title))
    ):
        raise TypeError(
            f"{metric.capitalize()} title must be a string or "
            "non-empty array of strings.")
    

def validate_description(
    description: str | list[str] | None, metric: str
) -> None:
    """
    Validates a description or descriptions, raising an error if invalid.
    Accepted: None, string, list of strings
    """
    if (
        description is not None and not isinstance(description, str)
        and not (
            isinstance(description, list) and description
            and all(isinstance(option, str) for option in description))
    ):
        raise TypeError(
            f"{metric.capitalize()} description must be a string or "
            "non-empty array of strings.")
    

def validate_numeric_markers(
    markers: dict[str, list], metric: str, int_only: bool = False
) -> None:
    """
    Checks all markers of a numeric metric are valid,
    including distance, moving/elapsed time, elevation etc.
    """
    if not isinstance(markers, dict):
        raise TypeError(f"{metric.capitalize()} markers must be a dictionary.")
    for key, categories in markers.items():
        if not valid_marker_key(key):
            raise ValueError(
                f"{metric.capitalize()} markers must be "
                "alphanumeric only (alongside underscores)")
        if not isinstance(categories, list):
            raise TypeError(
                f"{metric.capitalize()} markers categories must be an array.")
        for category in categories:
            if not isinstance(category, list):
                raise TypeError(
                    f"{metric.capitalize()} categories must be arrays.")
            if len(category) == 3:
                lower, upper, title = category
                description = None
            elif len(category) == 4:
                lower, upper, title, description = category
            else:
                raise ValueError(f"Invalid {metric} category found.")
            if lower is not None or upper is not None:
                if lower is None:
                    raise ValueError(f"Min {metric} cannot be null alone.")
                if not int_only and not isinstance(lower, numbers.Number):
                    raise ValueError(f"Min {metric} must be numeric.")
                if int_only and not isinstance(lower, int):
                    raise ValueError(f"Min {metric} must be an integer.")
                if lower < 0:
                    raise ValueError(f"Min {metric} must be non-negative")
                if upper is not None:
                    if not int_only and not isinstance(upper, numbers.Number):
                        raise ValueError(f"Max {metric} must be numeric.")
                    if int_only and not isinstance(upper, int):
                        raise ValueError(f"Max {metric} must be an integer.")
                    if upper <= lower:
                        raise ValueError(
                            f"Max {metric} must be greater than min {metric}.")
            validate_title(title, metric)
            validate_description(description, metric)
    

def validate_distance_markers(distance_markers: dict[str, list]) -> None:
    """Checks all distance markers are valid."""
    validate_numeric_markers(distance_markers, "distance")


def validate_moving_time_markers(moving_time_markers: dict[str, list]) -> None:
    """Checks all moving time markers are valid."""
    validate_numeric_markers(moving_time_markers, "moving time", True)


def validate_elapsed_time_markers(
    elapsed_time_markers: dict[str, list]
) -> None:
    """Checks all elapsed time markers are valid."""
    validate_numeric_markers(elapsed_time_markers, "elapsed time", True)


def validate_pace_markers(pace_markers: dict[str, list]) -> None:
    """Checks all pace markers are valid."""
    validate_numeric_markers(pace_markers, "pace")


def validate_elevation_markers(elevation_markers: dict[str, list]) -> None:
    """Checks all elevation markers are valid."""
    validate_numeric_markers(elevation_markers, "elevation")


def validate_elevation_per_km_markers(
    elevation_per_km_markers: dict[str, list]
) -> None:
    """Checks all elevation per km markers are valid."""
    validate_numeric_markers(elevation_per_km_markers, "elevation per km")


def validate_cadence_markers(cadence_markers: dict[str, list]) -> None:
    """Checks all cadence markers are valid."""
    validate_numeric_markers(cadence_markers, "cadence")


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
        validate_client_id(client_id)
    except KeyError:
        raise ValueError("Client ID not provided.")
    try:
        client_secret = data["client_secret"]
        validate_client_secret(client_secret)
    except KeyError:
        raise ValueError("Client secret not provided.")
    
    refresh_minutes = data.get("refresh_minutes", DEFAULT_REFRESH_MINUTES)
    validate_refresh_minutes(refresh_minutes)

    markers = data.get("markers")
    if markers is not None:
        if not isinstance(markers, dict):
            raise TypeError("Markers must be a dictionary.")
        distance_markers = markers.get("distance", {})
        if distance_markers != {}:
            validate_distance_markers(distance_markers)
        moving_time_markers = markers.get("moving_time", {})
        if moving_time_markers != {}:
            validate_moving_time_markers(moving_time_markers)
        elapsed_time_markers = markers.get("elapsed_time", {})
        if elapsed_time_markers != {}:
            validate_elapsed_time_markers(elapsed_time_markers)
        pace_markers = markers.get("pace", {})
        if pace_markers != {}:
            validate_pace_markers(pace_markers)
        elevation_markers = markers.get("elevation", {})
        if elevation_markers != {}:
            validate_elevation_markers(elevation_markers)
        elevation_per_km_markers = markers.get("elevation_per_km", {})
        if elevation_per_km_markers != {}:
            validate_elevation_per_km_markers(elevation_per_km_markers)
        cadence_markers = markers.get("cadence", {})
        if cadence_markers != {}:
            validate_cadence_markers(cadence_markers)

    heart_rate_zones = data.get("hr_zones")
    if heart_rate_zones is not None:
        validate_heart_rate_zones(heart_rate_zones)
        heart_rate_zones = {
            int(zone): heart_rate
            for zone, heart_rate in heart_rate_zones.items()}

    return Config(client_id, client_secret, refresh_minutes)
