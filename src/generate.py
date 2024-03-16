"""
Module to generate the title and description of a particular
activity if possible, based on the configuration details.
"""
import array
import ctypes
import platform
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
    templates = sorted(config.templates or [], key=priority_key)
    for template in templates:
        if (
            template.restriction is not None
            and not passes_restriction(activity_, template.restriction)
        ):
            continue
