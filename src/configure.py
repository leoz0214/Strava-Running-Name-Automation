"""
Module for parsing and building the configuration settings,
including deep validation.
"""
import datetime as dt
import itertools
import json
import numbers
import string
from dataclasses import dataclass
from typing import Callable

from const import CONFIG_FILE


# Sensible ranges/defaults.
MIN_REFRESH_MINUTES = 2
MAX_REFRESH_MINUTES = 60
DEFAULT_REFRESH_MINUTES = 5
MIN_HEART_RATE = 50
MAX_HEART_RATE = 250
# Hard-coded HR zones / weather string which can be placeholders.
HR_ZONES_PLACEHOLDER = "hr_zones"
WEATHER_PLACEHOLDER = "weather"
# Latitude/longitude limits, default point radius in metres.
MAX_ABS_LATITUDE = 90
MAX_ABS_LONGITUDE = 180
DEFAULT_POINT_RADIUS = 25


@dataclass
class Markers:
    """All markers for each metric stored in one data class."""
    distance: dict[str, list]
    moving_time: dict[str, list]
    elapsed_time: dict[str, list]
    pace: dict[str, list]
    start_time: dict[str, list]
    date: dict[str, list]
    elevation: dict[str, list]
    elevation_per_km: dict[str, list]
    cadence: dict[str, list]


@dataclass
class Config:
    """All configuration data stored in one data class."""
    client_id: int
    client_secret: str
    refresh_minutes: int
    markers: Markers | None


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


def validate_markers(
    markers: dict[str, list], metric: str, validate_category_function: Callable
) -> None:
    """
    Checks all markers of a particular metric are valid,
    including a validation function for each category.
    """
    if not isinstance(markers, dict):
        raise TypeError(f"{metric.capitalize()} markers must be a dictionary.")
    for key, categories in markers.items():
        if not valid_marker_key(key):
            raise ValueError(
                f"{metric.capitalize()} markers must be "
                "alphanumeric only (alongside underscores).")
        if not isinstance(categories, list):
            raise TypeError(
                f"{metric.capitalize()} markers categories must be an array.")
        for category in categories:
            if not isinstance(category, list):
                raise TypeError(
                    f"{metric.capitalize()} categories must be arrays.")
            validate_category_function(category)


def validate_numeric_category(
    category: list, metric: str, int_only: bool
) -> None:
    """Validates a numeric category in the format [min, max, title, (desc)]."""
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


def valid_hhmm_string(time_: str) -> bool:
    """Returns True if a time string is indeed strictly 24-hour HHMM."""
    return (
        len(time_) == len("HHMM") and time_.isdigit()
        and 0 <= int(time_[:2]) <= 23 and 0 <= int(time_[2:]) <= 59)


def validate_start_time_category(category: list, metric: str) -> None:
    """
    Validates a start time category in the format [min, max, title, (desc)]
    Times must be a string in the format HHMM, valid 24h time.
    Overlap into different days possible e.g. 2300 -> 0100.
    """
    if len(category) == 3:
        lower, upper, title = category
        description = None
    elif len(category) == 4:
        lower, upper, title, description = category
    else:
        raise ValueError(f"Invalid {metric} category found.")
    if lower is not None or upper is not None:
        if not isinstance(lower, str):
            raise TypeError(f"Min {metric} must be a HHMM string.")
        if not isinstance(upper, str):
            raise TypeError(f"Max {metric} must be a HHMM string.")
        if not valid_hhmm_string(lower):
            raise ValueError(f"Min {metric} must be a 24-hour HHMM string.")
        if not valid_hhmm_string(upper):
            raise ValueError(f"Max {metric} must be a 24-hour HHMM string.")
        if lower == upper:
            raise ValueError(f"Min {metric} must not equal max {metric}.")
    validate_title(title, metric)
    validate_description(description, metric)


def valid_yyyy_mm_dd_string(date: str) -> bool:
    """
    Returns True if the date is a valid YYYY-MM-DD date string.
    Asterisks indicate placeholders.
    """
    if date.count("-") != 2:
        return False
    year, month, day = date.split("-")
    if year == "*":
        # Use leap year if year is *, in case month is 2 and day is 29.
        year = "2024"
    if month == "*":
        # Use a month with 31 days in case day is 31.
        month = "01"
    if day == "*":
        # Use a day number 29 or less in case month is Feb.
        day = "01"
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return False
    try:
        # Tries to create a date object - if successful, valid, otherwise not.
        dt.date(int(year), int(month), int(day))
        return True
    except ValueError:
        return False


def validate_date_category(category: list, metric: str) -> None:
    """
    Validates a date category in the format [date, title, (desc)].
    date is a string in the format YYYY-MM-DD where YYYY, MM and DD
    can be replaced with asterisk placeholders to capture matching dates.
    Valid examples: 2024-03-11, *-12-25, *-*-01, *-02-*, *-*-*
    For example, *-12-25 will capture any year on December 25th.
    """
    if len(category) == 2:
        date, title = category
        description = None
    elif len(category) == 3:
        date, title, description = category
    else:
        raise ValueError(f"Invalid {metric} category found.")
    if date is not None:
        error_message = (
            f"{metric.capitalize()} must be a YYYY-MM-DD string "
            "(asterisk placeholders allowed).")
        if not isinstance(date, str):
            raise TypeError(error_message)
        if not valid_yyyy_mm_dd_string(date):
            raise ValueError(error_message)
    validate_title(title, metric)
    validate_description(description, metric)
    

def validate_numeric_markers(
    markers: dict[str, list], metric: str, int_only: bool = False
) -> None:
    """
    Checks all markers of a numeric metric are valid,
    including distance, moving/elapsed time, elevation etc.
    """
    validate_category_function = (
        lambda marker: validate_numeric_category(marker, metric, int_only))
    validate_markers(markers, metric, validate_category_function)


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


def validate_start_time_markers(start_time_markers: dict[str, list]) -> None:
    """Checks all start time markers are valid."""
    validate_category_function = (
        lambda category: validate_start_time_category(category, "start time"))
    validate_markers(
        start_time_markers, "start time", validate_category_function)
    

def validate_date_markers(date_markers: dict[str, list]) -> None:
    """Checks all date markers are valid."""
    validate_category_function = (
        lambda category: validate_date_category(category, "date"))
    validate_markers(date_markers, "date", validate_category_function)


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


def valid_placeholder(placeholder: str, markers: Markers) -> bool:
    """
    Returns True if a placeholder string is valid.
    Specify marker_type.key and HR zones and weather placeholders
    inside curly brackets, use double curly brackets to escape.
    Format checking is performed to ensure correctness.
    """
    if placeholder in (HR_ZONES_PLACEHOLDER, WEATHER_PLACEHOLDER):
        return True
    if placeholder.count(".") != 1:
        return False
    marker_metric, key = placeholder.split(".")
    return key in getattr(markers, marker_metric, {})


def validate_placeholder_string(
    placeholder_string: str, field: str, markers: Markers, is_route: bool
) -> None:
    """Ensures title/description format string is indeed valid."""
    curly_brackets_opened = False
    label = "route template" if is_route else "template"
    invalid_message = f"Invalid {label} {field} placeholder string."
    # This variable keeps track of consecutive curly brackets
    # such that consecutive curly brackets are escaped (not opening).
    opening_curly_brackets_streak = False
    start_i = None
    for i in range(len(placeholder_string)):
        if placeholder_string[i] == "{":
            if curly_brackets_opened:
                # Cannot open placeholder again if already opened.
                raise ValueError(invalid_message)
            elif (
                (i == len(placeholder_string) - 1
                    or placeholder_string[i+1] != "{")
                and not opening_curly_brackets_streak
            ):
                # Standalone curly bracket (opening of placeholder).
                curly_brackets_opened = True
                start_i = i + 1
            else:
                opening_curly_brackets_streak = True
        else:
            opening_curly_brackets_streak = False
        if placeholder_string[i] == "}" and curly_brackets_opened:
            # Closing of placeholder.
            placeholder = placeholder_string[start_i:i]
            if not valid_placeholder(placeholder, markers):
                raise ValueError(
                    f"Invalid placeholder for {label} "
                    f"{field}: '{placeholder}'")
            curly_brackets_opened = False
    if curly_brackets_opened:
        # End of string reached with curly brackets still open.
        raise ValueError(invalid_message)
    

def validate_template_restriction(restriction: dict, is_route: bool) -> None:
    """
    Validates a template restriction dictionary.
    Make a template only applicable for activities in a certain
    distance, pace or start time range.
    """
    label = "Route template" if is_route else "Template"
    if not isinstance(restriction, dict):
        raise TypeError(f"{label} restriction must be a dictionary.")
    for key, metric in (
        ("distance", "distance"),
        ("pace", "pace"),
        ("start_time", "start time")
    ):
        metric_restriction = restriction.get(key)
        if metric_restriction in (None, []):
            continue
        if not isinstance(metric_restriction, list):
            raise TypeError(
                f"{label} {metric} restrictions must be an array.")
        metric_ranges = (
            metric_restriction if isinstance(metric_restriction[0], list)
                else [metric_restriction])
        for metric_range in metric_ranges:
            if not isinstance(metric_range, list):
                raise TypeError(
                    f"{label} {metric} restriction range must be an array.")
            if len(metric_range) != 2:
                raise ValueError(
                    f"{label} {metric} restriction range array "
                    "must be length 2.")
            lower, upper = metric_range
            if key == "start_time":
                # Validate start times.
                for bound, start_time in (("min", lower), ("max", upper)):
                    if not isinstance(start_time, str):
                        raise TypeError(
                            f"{label} {bound} {metric} must be a HHMM string.")
                    if not valid_hhmm_string(start_time):
                        raise ValueError(
                            f"{label} {bound} {metric} "
                            "must be a 24-hour HHMM string.")
                if lower == upper:
                    raise ValueError(
                        f"{label} min {metric} must not equal max {metric}.")
                continue
            # Validate distance/pace ranges.
            if lower is None:
                raise TypeError(f"{label} min {metric} cannot be null.")
            if not isinstance(lower, numbers.Number):
                raise TypeError(f"{label} min {metric} must be numeric.")
            if lower < 0:
                raise ValueError(
                    f"{label} min {metric} must be non-negative.")
            if upper is not None:
                if not isinstance(upper, numbers.Number):
                    raise TypeError(f"{label} max {metric} must be numeric.")
                if upper <= lower:
                    raise ValueError(
                        f"{label} max {metric} must be "
                        f"greater than min {metric}.")
    if is_route:
        # Route restrictions also may contain blacklist of points.
        blacklist_points = restriction.get("blacklist")
        validate_points(blacklist_points, is_blacklist=True)


def validate_template(
    template: dict, markers: Markers, is_route: bool = False
) -> None:
    """
    Checks a template dictionary is valid.
    is_route set to True means the template is a route template,
    using this function to avoid repetition.
    """
    label = "Route template" if is_route else "Template"
    if not isinstance(template, dict):
        raise TypeError(f"{label} must be a dictionary.")
    for key in ("title", "description"):
        placeholder_string = template.get(key)
        if placeholder_string in (None, []):
            raise ValueError(f"{label} {key} must be provided.")
        elif isinstance(placeholder_string, str):
            validate_placeholder_string(
                placeholder_string, key, markers, is_route)
        elif isinstance(placeholder_string, list):
            # Multiple strings for fallback purposes.
            for option in placeholder_string:
                if not isinstance(option, str):
                    raise TypeError(f"{label} {key} must be a string.")
                validate_placeholder_string(option, key, markers, is_route)
        else:
            raise TypeError(
                f"{label} {key} must be a string or array of strings.")
    priority = template.get("priority")
    if priority is not None and not isinstance(priority, int):
        raise TypeError(f"{label} priority must be an integer.")
    restriction = template.get("restrict")
    if restriction is not None:
        validate_template_restriction(restriction, is_route)


def validate_points(
    points: list[list[float]] | None, is_blacklist: bool = False
) -> None:
    """
    Validates a list of points in the format [lat, long, (radius)],
    either as the route required points or route blacklist of points.
    """
    label = "blacklist point" if is_blacklist else "point"
    # Main list of points must be non-empty array.
    # Blacklist can be null or empty array, but not other types.
    if not is_blacklist and not isinstance(points, list):
        raise TypeError(f"Route template {label} must be a non-empty array.")
    if is_blacklist:
        if points is None:
            return
        if not isinstance(points, list):
            raise TypeError(f"Route template {label} must be an array.")
    for point in points:
        if not isinstance(point, list):
            raise TypeError(f"Route template {label} must be an array.")
        if len(point) == 2:
            latitude, longitude = point
            radius = DEFAULT_POINT_RADIUS
        elif len(point) == 3:
            latitude, longitude, radius = point
        else:
            raise ValueError(f"Invalid route template {label} found.")
        if not isinstance(latitude, numbers.Number):
            raise TypeError(
                f"Route template {label} latitude must be numeric.")
        if abs(latitude) > MAX_ABS_LATITUDE:
            raise ValueError(f"Route template {label} latitude out of range.")
        if not isinstance(longitude, numbers.Number):
            raise TypeError(
                f"Route template {label} longitude must be numeric.")
        if abs(longitude) > MAX_ABS_LONGITUDE:
            raise ValueError(f"Route template {label} longitude out of range.")
        if not isinstance(radius, numbers.Number):
            raise TypeError(f"Route template {label} radius must be numeric.")
        if radius <= 0:
            raise TypeError(f"Route template {label} radius must be positive.")


def validate_route_template(route_template: dict, markers: Markers) -> None:
    """
    Checks a route template dictionary is valid.
    A route template is an extension to a standard template except
    a list of lat/long points need to be reached in the route for a template
    to be valid. As exact matching is impractical, a radius (margin of error)
    can be set, where any point in the run within that radius is accepted.
    """
    validate_template(route_template, markers, is_route=True)
    points = route_template.get("points")
    validate_points(points)


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
        start_time_markers = markers.get("start_time", {})
        if start_time_markers != {}:
            validate_start_time_markers(start_time_markers)
        date_markers = markers.get("date", {})
        if date_markers != {}:
            validate_date_markers(date_markers)
        elevation_markers = markers.get("elevation", {})
        if elevation_markers != {}:
            validate_elevation_markers(elevation_markers)
        elevation_per_km_markers = markers.get("elevation_per_km", {})
        if elevation_per_km_markers != {}:
            validate_elevation_per_km_markers(elevation_per_km_markers)
        cadence_markers = markers.get("cadence", {})
        if cadence_markers != {}:
            validate_cadence_markers(cadence_markers)
        markers = Markers(
            distance_markers, moving_time_markers, elapsed_time_markers,
            pace_markers, start_time_markers, date_markers,
            elevation_markers, elevation_per_km_markers, cadence_markers)
    
    templates = data.get("templates")
    if templates is not None:
        if not isinstance(templates, list):
            raise TypeError("Templates must be an array.")
        for template in templates:
            validate_template(template, markers)

    route_templates = data.get("route_templates")
    if route_templates is not None:
        if not isinstance(route_templates, list):
            raise TypeError("Route templates must be an array.")
        for route_template in route_templates:
            validate_route_template(route_template, markers)
    print(route_templates)

    heart_rate_zones = data.get("hr_zones")
    if heart_rate_zones is not None:
        validate_heart_rate_zones(heart_rate_zones)
        heart_rate_zones = {
            int(zone): heart_rate
            for zone, heart_rate in heart_rate_zones.items()}

    return Config(client_id, client_secret, refresh_minutes, markers)
