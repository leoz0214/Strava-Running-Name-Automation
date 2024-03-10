"""
Module responsible for fetching recent activities and updating activity data.
This includes tracking seen activities to avoid re-fetching.
Also provides the Activity data class for obtaining various activity metrics.
"""
import datetime as dt
from dataclasses import dataclass

import api
from const import SEEN_ACTIVITIES_FILE


GET_ACTIVITIES_URL = f"{api.API_URL}/athlete/activities"
GET_ACTIVITY_URL = api.API_URL + "/activities/{id}"
# Maximum number of recent activities to scan.
RECENT_ACTIVITIES_COUNT = 5
# Approximate maximum seen activities to store (may be slightly more).
# This is to prevent the file becoming big over time.
# Recording this many activities as processed is fine because
# reasonable usage of the program will not re-process very old activities.
MAX_SEEN_ACTIVITIES_COUNT = 1000
# Isoformat date length without time zone info.
ISO_DATE_LENGTH = len("YYYY-MM-DDTHH:MM:SS")


@dataclass
class Activity:
    """Activity data class - distance, pace, elevation, date/time etc."""


def get_seen_activities() -> set[int]:
    """Returns a set of activity IDs already processed by the program."""
    if not SEEN_ACTIVITIES_FILE.is_file():
        return set()
    with SEEN_ACTIVITIES_FILE.open("r", encoding="utf8") as f:
        return set(f.read().splitlines()[-MAX_SEEN_ACTIVITIES_COUNT:])


def update_seen_activities(seen_activities: set[int]) -> None:
    """Updates the seen activities file."""
    with SEEN_ACTIVITIES_FILE.open("w", encoding="utf8") as f:
        f.write("\n".join(map(str, sorted(seen_activities))))


def get_activity(activity_id: int, access_token: str) -> Activity:
    """Fetches detailed activity info and returns an Activity object."""
    url = GET_ACTIVITY_URL.format(id=activity_id)
    params = {"access_token": access_token}
    data = api.get(url, params, api.is_status_200).json()
    title = data["name"]
    description = data["description"]
    activity_type = data["type"]
    distance = data["distance"] / 1000 # m to km
    moving_time = data["moving_time"]
    elapsed_time = data["elapsed_time"]
    pace = moving_time / distance # s/km
    start_date_time = dt.datetime.fromisoformat(
        data["start_date_local"][:ISO_DATE_LENGTH]) # Ignore time zone info.
    elevation = data["total_elevation_gain"]
    elevation_per_km = elevation / distance if elevation is not None else None
    cadence = data["average_cadence"] * 2 # One -> both feet steps.

    # TODO - HR stream info, lat/long stream info, BBC weather integration.


def get_activities(access_token: str) -> list[Activity]:
    """Returns list of recent activities not already seen by the program."""
    params = {
        "access_token": access_token,
        "per_page": RECENT_ACTIVITIES_COUNT
    }
    response = api.get(GET_ACTIVITIES_URL, params, api.is_status_200).json()
    seen_activities = get_seen_activities()
    activities = []
    for activity_dict in response:
        activity_id = activity_dict["id"]
        if activity_id in seen_activities:
            continue
        seen_activities.add(activity_id)
        activity = get_activity(activity_id, access_token)
        activities.append(activity)
    if activities:
        update_seen_activities(seen_activities)
    return activities
