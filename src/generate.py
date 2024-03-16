"""
Module to generate the title and description of a particular
activity if possible, based on the configuration details.
"""
import activity
import configure
from utils import hhmm_to_minutes, haversine_distance


priority_key = lambda template: (
    float("inf") if template.priority is None else template.priority)


def point_touched(
    point: configure.Point, lat_long_stream: list[list[float]]
) -> bool:
    """Returns True if any lat/long coordinate is in range of given point."""
    return any(
        haversine_distance(
            point.latitude, point.longitude, lat, long) * 1000 <= point.radius
        for lat, long in lat_long_stream)


def any_point_touched(
    points: list[configure.Point], lat_long_stream: list[list[float]]
) -> bool:
    """
    Returns True if any activity lat/long point is
    within any configuration point with a set radius.
    """
    return any(point_touched(point, lat_long_stream) for point in points)


def all_points_touched(
    points: list[configure.Point], lat_long_stream: list[list[float]]
) -> bool:
    """
    Returns True if ALL configuration points are reached in the
    stream of latitude and longitude points.
    """
    return all(point_touched(point, lat_long_stream) for point in points)


def passes_restriction(
    activity_: activity.Activity,
    restriction: configure.Restriction | configure.RouteRestriction
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
        if isinstance(restriction.start_time, list):
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
        return not any_point_touched(
            restriction.blacklist, activity_.lat_long_stream)
    return True


def matching_route_template(
    activity_: activity.Activity, route_template: configure.RouteTemplate
) -> bool:
    """
    Deduce if a route template is valid for a particular activity on a
    basic level - restrictions pass and all points touched.
    """
    restriction = route_template.restriction
    return (
        restriction is None or passes_restriction(activity_, route_template)
        and all_points_touched(
            route_template.points, activity_.lat_long_stream))


def generate_title_and_description(
    activity_: activity.Activity, config: configure.Config
) -> tuple[str, str]:
    """
    Given an activity and the config info, a title and description is generated
    using a suitable template if possible. If a title and description cannot
    be generated, an error is raised.
    """
    if activity_.lat_long_stream is not None:
        route_templates = sorted(
            config.route_templates or [], key=priority_key)
        for route_template in route_templates:
            if not matching_route_template(activity_, route_template):
                continue
    templates = sorted(config.templates or [], key=priority_key)
    for template in templates:
        if (
            template.restriction is not None
            and not passes_restriction(activity_, template.restriction)
        ):
            continue
