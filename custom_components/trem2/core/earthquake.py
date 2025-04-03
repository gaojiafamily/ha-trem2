"""Calculate Earthquake for Taiwan Real-time Earthquake Monitoring integration."""

import math
from math import atan2, cos, radians, sin, sqrt

from .const import COUNTY_CENTERS, COUNTY_SITE_VALUES, EARTH_RADIUS, TAIWAN_CENTER


def calculate_distance(lat1, lon1, lat2, lon2) -> float:
    """Calculate the distance between two points on the Earth using the Haversine formula."""

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2

    return 2 * atan2(sqrt(a), sqrt(1 - a))


def calculate_intensity(
    magnitude: float, hypocenter_distance: float, depth: int, site_effect: float = 1.751
) -> float:
    """Calculate the intensity of an earthquake based on its magnitude, hypocenter distance, and depth."""

    pga = (
        1.657
        * math.exp(1.533 * magnitude)
        * hypocenter_distance**-1.607
        * (site_effect or 1.751)
    )
    i = 2 * math.log10(pga) + 0.7

    if i > 3:
        long = 10 ** (0.5 * magnitude - 1.85) / 2
        x = max(hypocenter_distance - long, 3)
        gpv600 = 10 ** (
            0.58 * magnitude
            + 0.0038 * depth
            - 1.29
            - math.log10(x + 0.0028 * 10 ** (0.5 * magnitude))
            - 0.002 * x
        )
        arv = 1.0
        pgv400 = gpv600 * 1.31
        pgv = pgv400 * arv
        i = 2.68 + 1.72 * math.log10(pgv)

    return i


def round_intensity(intensity: float) -> int:
    """Round the intensity to the nearest whole number based on specific thresholds."""

    if intensity <= 0:
        return 0
    if intensity < 4.5:
        return round(intensity)
    if intensity < 5:
        return 5
    if intensity < 5.5:
        return 6
    if intensity < 6:
        return 7
    if intensity < 6.5:
        return 8

    return 9


def intensity_to_text(intensity) -> str:
    """Convert intensity to text on specific thresholds."""

    if isinstance(intensity, float):
        intensity = round_intensity(intensity)

    if intensity == 0:
        return "0級"
    if intensity == 1:
        return "1級"
    if intensity == 2:
        return "2級"
    if intensity == 3:
        return "3級"
    if intensity == 4:
        return "4級"
    if intensity == 5:
        return "5弱"
    if intensity == 6:
        return "5強"
    if intensity == 7:
        return "6弱"
    if intensity == 8:
        return "6強"

    return "7級"


def get_calculate_intensity(eq_data: dict) -> dict:
    """Calculate the intensity of an earthquake based on its data."""

    depth = eq_data.get("depth", 0)
    lat = eq_data.get("lat", TAIWAN_CENTER[0])
    lon = eq_data.get("lon", TAIWAN_CENTER[1])
    mag = eq_data.get("mag", 0)

    intensity_map = {}

    squared_depth = depth**2

    for county_id, (county_lat, county_lon) in COUNTY_CENTERS.items():
        site_effect = COUNTY_SITE_VALUES.get(county_id, 1.751)
        distance_in_radians = calculate_distance(lat, lon, county_lat, county_lon)
        real_distance = sqrt((distance_in_radians * EARTH_RADIUS) ** 2 + squared_depth)

        intensity_map[county_id] = calculate_intensity(
            mag, real_distance, depth, site_effect
        )

    return intensity_map
