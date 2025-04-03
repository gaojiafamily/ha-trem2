# earthquake.py
import math
from math import radians, sin, cos, sqrt, atan2
from const import COUNTY_CENTERS, COUNTY_SITE_VALUES, EARTH_RADIUS

# 計算震央距離（Haversine 公式）
def calculate_distance(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return c

# 計算預計震度
def calculate_intensity(magnitude: float, hypocenter_distance: float, depth: int, site_effect:float = 1.751) -> float:
    pga = 1.657 * math.exp(1.533 * magnitude) * hypocenter_distance**-1.607 * (site_effect or 1.751)
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
    if intensity < 0:
        return 0
    elif intensity < 4.5:
        return round(intensity)
    elif intensity < 5:
        return 5
    elif intensity < 5.5:
        return 6
    elif intensity < 6:
        return 7
    elif intensity < 6.5:
        return 8
    else:
        return 9

# 各縣市的預計震度
def get_calculate_intensity(eq_data) -> dict:
    depth = eq_data["depth"]
    lat = eq_data["lat"]
    lon = eq_data["lon"]
    mag = eq_data["mag"]

    intensity_map = {}

    squared_depth = depth**2

    for county_id, (county_lat, county_lon) in COUNTY_CENTERS.items():
        site_effect = COUNTY_SITE_VALUES.get(county_id, 1.751)
        distance_in_radians = calculate_distance(lat, lon, county_lat, county_lon)
        real_distance = sqrt((distance_in_radians * EARTH_RADIUS) ** 2 + squared_depth)

        intensity = calculate_intensity(mag, real_distance, depth, site_effect)
        intensity_map[county_id] = round_intensity(intensity)

    return intensity_map