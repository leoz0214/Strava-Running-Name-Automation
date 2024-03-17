"""
Module to generate the title and description of a particular
activity if possible, based on the configuration details.
"""
import array
import ctypes
import platform
import random
from contextlib import suppress
from typing import Callable

import activity
import configure
from const import GEO_DLL_FILE, GEO_SO_FILE
from utils import hhmm_to_minutes, haversine_distance


priority_key = lambda template: (
    float("inf") if template.priority is None else template.priority)

# Load C++ functions if possible (for performance purposes).
try:
    file = {"Windows": GEO_DLL_FILE, "Linux": GEO_SO_FILE}[platform.system()]
    c_geo_library = ctypes.CDLL(str(file))
    c_any_point_touched = c_geo_library.any_point_touched
    c_any_point_touched.restype = ctypes.c_bool
    c_all_points_touched = c_geo_library.all_points_touched
    c_all_points_touched.restype = ctypes.c_bool
except Exception:
    print("Warning: Not using C++ geo library which would be faster.")
    c_geo_library = None
    c_any_point_touched = None
    c_all_points_touched = None


def point_touched(
    point: configure.Point, lat_long_stream: list[list[float]]
) -> bool:
    """
    Returns True if any lat/long coordinate is in range of given point.
    Fallback if faster C++ code is not available.
    """
    return any(
        haversine_distance(
            point.latitude, point.longitude, lat, long) * 1000 <= point.radius
        for lat, long in lat_long_stream)


def get_c_lat_long_array(lat_long_stream: list[list[float]]) -> ctypes.Array:
    """Returns lat/long stream as C-array of doubles for C++ processing."""
    lat_long_list = []
    for lat_long in lat_long_stream:
        lat_long_list.extend(lat_long)
    lat_long_array = array.array("d", lat_long_list)
    return (ctypes.c_double * len(lat_long_array)).from_buffer(lat_long_array)


def c_points_check(
    points: list[configure.Point],
    c_lat_long_array: ctypes.Array[ctypes.c_double], c_function: Callable
) -> bool:
    """Performs any/all point(s) check by calling appropriate C++ function."""
    points_list = []
    for point in points:
        points_list.extend((point.latitude, point.longitude, point.radius))
    points_array = array.array("d", points_list)
    c_points_array = (
        ctypes.c_double * len(points_array)).from_buffer(points_array)
    points_pointer = ctypes.c_void_p(ctypes.addressof(c_points_array))
    lat_long_pointer = ctypes.c_void_p(ctypes.addressof(c_lat_long_array))
    result = c_function(
        points_pointer, lat_long_pointer,
        ctypes.c_uint(len(points)), ctypes.c_uint(len(c_lat_long_array) // 3))
    return result


def any_point_touched(
    points: list[configure.Point],
    lat_longs: list[list[float]] | ctypes.Array[ctypes.c_double]
) -> bool:
    """
    Returns True if any activity lat/long point is
    within any configuration point with a set radius.
    """
    if c_any_point_touched is None:
        # Python fallback (slower but better than unavailable).
        return any(point_touched(point, lat_longs) for point in points)
    return c_points_check(points, lat_longs, c_any_point_touched)


def all_points_touched(
    points: list[configure.Point],
    lat_longs: list[list[float]] | ctypes.Array[ctypes.c_double]
) -> bool:
    """
    Returns True if ALL configuration points are reached in the
    stream of latitude and longitude points.
    """
    if c_all_points_touched is None:
        return all(point_touched(point, lat_longs) for point in points)
    return c_points_check(points, lat_longs, c_all_points_touched)


def passes_restriction(
    activity_: activity.Activity,
    restriction: configure.Restriction | configure.RouteRestriction,
    lat_longs: list[list[float]] | ctypes.Array[ctypes.c_double] = None
) -> bool:
    """Returns True if an activity meets the restriction criteria."""
    for restriction_category, value in (
        (restriction.distance, activity_.distance),
        (restriction.pace, activity_.pace)
    ):
        if not restriction_category:
            continue
        if isinstance(restriction_category[0], list):
            intervals = restriction_category
        else:
            intervals = [restriction_category]
        if not any(lower <= value <= upper for lower, upper in intervals):
            return False
    if restriction.start_time:
        if isinstance(restriction.start_time[0], list):
            start_time_intervals = restriction.start_time
        else:
            start_time_intervals = [restriction.start_time]
        start_time_minutes = (
            activity_.start_date_time.hour * 60
            + activity_.start_date_time.minute)
        for lower, upper in start_time_intervals:
            lower_minutes = hhmm_to_minutes(lower)
            upper_minutes = hhmm_to_minutes(upper)
            if upper_minutes < lower_minutes:
                # Cycle to next day e.g. 2300 -> 0200: 2330, 0030 are in range.
                if (
                    start_time_minutes <= upper_minutes
                    or start_time_minutes >= lower_minutes
                ):
                    break
            elif lower_minutes <= start_time_minutes <= upper_minutes:
                break
        else:
            return False
    if (
        isinstance(restriction, configure.RouteRestriction)
        and restriction.blacklist
    ):
        return not any_point_touched(restriction.blacklist, lat_longs)
    return True


def matching_route_template(
    activity_: activity.Activity, route_template: configure.RouteTemplate,
    lat_longs: list[list[float]] | ctypes.Array[ctypes.c_double]
) -> bool:
    """
    Deduce if a route template is valid for a particular activity on a
    basic level - restrictions pass and all points touched.
    """
    restriction = route_template.restriction
    return (
        restriction is None
        or passes_restriction(activity_, route_template.restriction, lat_longs)
        and all_points_touched(route_template.points, lat_longs))


def get_numeric_text(
    value: int | float | None, placeholder: str, config: configure.Config,
    is_description: bool
) -> str:
    """
    Returns title/description of a basic numeric metric in the format
    [min, max, title, (desc)]. Activity metric must be [min, max).
    """
    # [texts] - list of lists of texts.
    in_range_texts_list = []
    else_texts_list = []
    if value is None:
        # Set value to dummy -float(inf).
        value = -float("inf")
    metric, key = placeholder.split(".")
    intervals = getattr(config.markers, metric)[key]
    for interval in intervals:
        if len(interval) == 3:
            lower, upper, titles = interval
            descriptions = None
        else:
            lower, upper, titles, descriptions = interval
        if isinstance(titles, str):
            titles = [titles]
        if isinstance(descriptions, str):
            descriptions = [descriptions]
        if lower is None and upper is None:
            text_list = else_texts_list
        elif lower <= value < (float("inf") if upper is None else upper):
            text_list = in_range_texts_list
        else:
            continue
        if is_description and descriptions:
            text_list.append(descriptions)
        elif not is_description and titles:
            text_list.append(titles)
    if in_range_texts_list:
        return random.choice(random.choice(in_range_texts_list))
    elif else_texts_list:
        return random.choice(random.choice(else_texts_list))
    raise RuntimeError


def get_placeholder_value(
    activity_: activity.Activity, placeholder: str, config: configure.Config,
    is_description: bool
) -> str:
    """
    Takes a placeholder and interprets it in the context of an activity.
    Raises an error if the placeholder is not compatible with the activity.
    """
    metric = placeholder.split(".")[0] # metric.key - extract metric
    match metric:
        case configure.HR_ZONES_PLACEHOLDER:
            if activity_.heart_rate_stream is None:
                raise RuntimeError
            return ""
        case configure.WEATHER_PLACEHOLDER:
            if activity_.weather is None:
                raise RuntimeError
            return ""
        case "start_time":
            return ""
        case "date":
            return ""
        case _:
            value = {
                "distance": activity_.distance,
                "moving_time": activity_.moving_time,
                "elapsed_time": activity_.elapsed_time,
                "pace": activity_.pace,
                "elevation": activity_.elevation,
                "elevation_per_km": activity_.elevation_per_km,
                "cadence": activity_.cadence
            }[metric]
            return get_numeric_text(
                value, placeholder, config, is_description)


def format_placeholder_string(
    activity_: activity.Activity, placeholder_string: str,
    config: configure.Config, is_description: bool
) -> str:
    """
    Attempts to fill in a placeholder string with given text based on
    activity metrics. Raises an error upon failure e.g. placeholder string
    requires weather data, but the activity has no weather data.
    """
    # Use list to avoid inefficient string concatenation (join at end).
    result = []
    opening_curly_bracket_streak = False
    start_i = None
    # NOTE: validation already done beforehand on the string, no need to
    # do validation again - straight to the point.
    for i in range(len(placeholder_string)):
        if placeholder_string[i] == "{":
            if (
                i < len(placeholder_string) - 1
                and placeholder_string[i+1] != "{"
                and not opening_curly_bracket_streak
            ):
                start_i = i + 1
            else:
                opening_curly_bracket_streak = True
                result.append("{")
            continue
        opening_curly_bracket_streak = False
        if placeholder_string[i] == "}" and start_i is not None:
            placeholder = placeholder_string[start_i:i]
            placeholder_value = get_placeholder_value(
                activity_, placeholder, config, is_description)
            result.append(placeholder_value)
            start_i = None
            continue
        if start_i is None:
            result.append(placeholder_string[i])
    return "".join(result)


def generate_text(
    activity_: activity.Activity, placeholder_strings: str | list[str],
    config: configure.Config, is_description: bool = False
) -> str:
    """
    Attempts to generate a title/description given
    a single or list of placeholder strings. Raises an error if none
    of the placeholder strings can be applied to the given activity.
    """
    if isinstance(placeholder_strings, str):
        placeholder_strings = [placeholder_strings]
    for placeholder_string in placeholder_strings:
        with suppress(RuntimeError):
            return format_placeholder_string(
                activity_, placeholder_string, config, is_description)
    raise RuntimeError


def generate_title_and_description(
    activity_: activity.Activity, config: configure.Config
) -> tuple[str, str]:
    """
    Given an activity and the config info, a title and description is generated
    using a suitable template if possible. If a title and description cannot
    be generated, an error is raised.
    """
    if activity_.lat_long_stream is not None:
        lat_longs = activity_.lat_long_stream
        route_templates = sorted(
            config.route_templates or [], key=priority_key)
        if route_templates:
            if c_geo_library is not None:
                lat_longs = get_c_lat_long_array(lat_longs)
            for route_template in route_templates:
                if not matching_route_template(
                    activity_, route_template, lat_longs
                ):
                    continue
                with suppress(RuntimeError):
                    title = generate_text(
                        activity_, route_template.title, config)
                    description = generate_text(
                        activity_, route_template.description, config, True)
                    return title, description
    templates = sorted(config.templates or [], key=priority_key)
    for template in templates:
        if (
            template.restriction is not None
            and not passes_restriction(activity_, template.restriction)
        ):
            continue
        with suppress(RuntimeError):
            title = generate_text(activity_, template.title, config)
            description = generate_text(
                activity_, template.description, config, True)
            return title, description
    raise RuntimeError(
        f"No suitable template found for activity {activity_.id}, skipping...")
