"""
Module responsible for fetching recent activities and updating activity data.
This includes tracking seen activities to avoid re-fetching.
Also provides the Activity data class for obtaining various activity metrics.
"""
import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass

import api
from const import SEEN_ACTIVITIES_FILE, WEATHER_DB_FILE
from utils import haversine_distance


GET_ACTIVITIES_URL = f"{api.API_URL}/athlete/activities"
GET_ACTIVITY_URL = api.API_URL + "/activities/{id}"
GET_ACTIVITY_STREAMS_URL = api.API_URL + "/activities/{id}/streams"
# Maximum number of recent activities to scan.
RECENT_ACTIVITIES_COUNT = 5
# Approximate maximum seen activities to store (may be slightly more).
# This is to prevent the file becoming big over time.
# Recording this many activities as processed is fine because
# reasonable usage of the program will not re-process very old activities.
MAX_SEEN_ACTIVITIES_COUNT = 1000
# Isoformat date length without time zone info.
ISO_DATE_LENGTH = len("YYYY-MM-DDTHH:MM:SS")
# Maximum allowed distance between activity start position
# and weather forecast lat/long.
MAX_WEATHER_DISTANCE = 20
# Weather visibilites int to string as seen in the BBC Weather project.
VISIBILITIES = {
    0: "Very Poor", 1: "Poor", 2: "Moderate",
    3: "Good", 4: "Very Good", 5: "Excellent"
}
# From https://www.metoffice.gov.uk/services/data/datapoint/code-definitions
WEATHER_TYPES = {
    0: "Clear Sky", 1: "Sunny", 2: "Partly Cloudy", 3: "Sunny Intervals",
    5: "Mist", 6: "Fog", 7: "Light Cloud", 8: "Thick Cloud",
    9: "Light Rain Showers", 10: "Light Rain Showers",
    11: "Drizzle", 12: "Light Rain", 13: "Heavy Rain Showers",
    14: "Heavy Rain Showers", 15: "Heavy Rain",
    16: "Sleet Showers", 17: "Sleet Showers", 18: "Sleet",
    19: "Hail Showers", 20: "Hail Showers", 21: "Hail",
    22: "Light Snow Showers", 23: "Light Snow Showers", 24: "Light Snow",
    25: "Heavy Snow Showers", 26: "Heavy Snow Showers", 27: "Heavy Snow",
    28: "Thundery Showers", 29: "Thundery Showers", 30: "Thunder"
}
# Possible auto-generated titles (by time of day, as always seen).
DEFAULT_TITLES = (
    "Morning Run", "Lunch Run", "Afternoon Run", "Evening Run", "Night Run")


@dataclass
class Weather:
    """Weather data class - provides weather info for an activity."""
    weather_type: str
    temperature: int
    feels_like_temperature: int
    wind_speed: int
    wind_direction: str
    humidity: int
    pressure: int
    visibility: str


@dataclass
class Activity:
    """Activity data class - distance, pace, elevation, date/time etc."""
    id: int
    title: str
    description: str | None
    type: str
    distance: float
    moving_time: int
    elapsed_time: int
    pace: float
    start_date_time: dt.datetime
    elevation: float | None
    elevation_per_km: float | None
    cadence: float | None
    lat_long_stream: list[list[int]] | None
    heart_rate_stream: list[int] | None
    weather: Weather | None


def get_seen_activities() -> set[int]:
    """Returns a set of activity IDs already processed by the program."""
    if not SEEN_ACTIVITIES_FILE.is_file():
        return set()
    with SEEN_ACTIVITIES_FILE.open("r", encoding="utf8") as f:
        return set(
            map(int, f.read().splitlines()[-MAX_SEEN_ACTIVITIES_COUNT:]))


def update_seen_activities(seen_activities: set[int]) -> None:
    """Updates the seen activities file."""
    with SEEN_ACTIVITIES_FILE.open("w", encoding="utf8") as f:
        f.write("\n".join(map(str, sorted(seen_activities))))


def get_weather(
    date_time: dt.datetime, latitude: float, longitude: float
) -> Weather | None:
    """Returns weather data for an activity if available, else None."""
    if not WEATHER_DB_FILE.is_file():
        return None
    timestamp = date_time.replace(tzinfo=dt.timezone.utc).timestamp()
    with sqlite3.connect(WEATHER_DB_FILE) as conn:
        cursor = conn.cursor()
        location_records = cursor.execute(
            "SELECT location_id, latitude, longitude FROM locations"
        ).fetchall()
        min_distance = float("inf")
        location_id = None
        for location in location_records:
            distance = haversine_distance(
                latitude, longitude, location[1], location[2])
            if distance <= MAX_WEATHER_DISTANCE and distance < min_distance:
                min_distance = distance
                location_id = location[0]
        if location_id is None:
            # No suitable location in the database found.
            return None
        weather_records = cursor.execute(
            """
            SELECT timestamp, temperature, feels_like_temperature,
            wind_speed, wind_direction, humidity, pressure, visibility,
            weather_type FROM weather_times
            WHERE location_id = ? AND ABS(timestamp - ?) < 3600
            """, (location_id, timestamp)).fetchall()
    if not weather_records:
        # No data for the time of the activity obtained.
        return None
    # Select closest time to the activity, and unpack into variables.
    (
        _, temperature, feels_like_temperature, wind_speed,
        wind_direction, humidity, pressure, visibility, weather_type
    ) = min(weather_records, key=lambda record: abs(timestamp - record[0]))
    visibility = VISIBILITIES[visibility]
    weather_type = WEATHER_TYPES[weather_type]
    return Weather(
        weather_type, temperature, feels_like_temperature,
        wind_speed, wind_direction, humidity, pressure, visibility)


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
    cadence = (
        data["average_cadence"] * 2 if data["average_cadence"] is not None
        else None) # One -> both feet steps.

    stream_url = GET_ACTIVITY_STREAMS_URL.format(id=activity_id)
    keys = []
    has_location = bool(data["start_latlng"])
    if has_location:
        keys.append("latlng")
    if data["has_heartrate"]:
        keys.append("heartrate")
    if keys:
        params = {
            "access_token": access_token,
            "keys": keys,
            "key_by_type": True
        }
        stream_data = api.get(stream_url, params, api.is_status_200).json()
        lat_long_stream = stream_data.get("latlng", {}).get("data")
        heart_rate_stream = stream_data.get("heartrate", {}).get("data")
    else:
        lat_long_stream = None
        heart_rate_stream = None
    if has_location:
        weather = get_weather(start_date_time, *data["start_latlng"])
    else:
        weather = None
    return Activity(
        activity_id, title, description, activity_type,
        distance, moving_time, elapsed_time, pace, start_date_time, elevation,
        elevation_per_km, cadence, lat_long_stream, heart_rate_stream, weather)


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


def can_process_activity(activity: Activity) -> bool:
    """
    Returns True if an activity can be processed by the program.
    - The activity must be a run.
    - The title must be the default <time_of_day> Run
    - The description must be empty (None).
    """
    if activity.type != "Run":
        logging.info(
            f"Activity {activity.id} will not be processed because "
            f"it is not a Run, but a {activity.type}.")
        return False
    if activity.title not in DEFAULT_TITLES:
        logging.info(
            f"Activity {activity.id} will not be processed because "
            f"it has a non-default title: {activity.title}")
        return False
    if activity.description is not None:
        logging.info(
            f"Activity {activity.id} will not be processed because "
            "it has a non-empty description.")
        return False
    return True
