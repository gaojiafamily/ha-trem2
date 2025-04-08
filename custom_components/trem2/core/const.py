"""Constants for Taiwan Real-time Earthquake Monitoring integration."""

from datetime import UTC
from zoneinfo import ZoneInfo

TZ_TW = ZoneInfo("Asia/Taipei")
TZ_UTC = UTC

INTENSITY_COLORS = {
    1: "#387FFF",
    2: "#244FD0",
    3: "#35BF56",
    4: "#F8F755",
    5: "#FFC759",
    6: "#FF9935",
    7: "#DF443B",
    8: "#7B170F",
    9: "#7237C1",
}
DEFAULT_COLOR = "inherit"

EARTH_RADIUS = 6371.008
COUNTY_SITE_VALUES = {
    "TWKIN": 0.75,
    "TWLIE": 0.7,
    "TWPEN": 0.8,
    "TWTAO": 1.15,
    "TWHSQ": 1.1,
    "TWHSZ": 1.1,
    "TWMIA": 1.05,
    "TWTXG": 1.0,
    "TWNAN": 1.2,
    "TWCHA": 0.95,
    "TWYUN": 0.9,
    "TWCYQ": 0.85,
    "TWTNN": 0.95,
    "TWKHH": 0.9,
    "TWPIF": 0.9,
    "TWTTT": 1.25,
    "TWHUA": 1.3,
    "TWILA": 1.3,
    "TWNWT": 1.1,
    "TWKEE": 1.15,
    "TWTPE": 1.2,
    "TWCYI": 0.85,
}

TAIWAN_CENTER = (23.97565, 120.9738819)
COUNTY_CENTERS = {
    "TWKIN": (24.43, 118.32),
    "TWLIE": (26.15, 119.92),
    "TWPEN": (23.57, 119.58),
    "TWTAO": (24.99, 121.31),
    "TWHSQ": (24.84, 121.01),
    "TWHSZ": (24.80, 120.97),
    "TWMIA": (24.56, 120.82),
    "TWTXG": (24.14, 120.68),
    "TWNAN": (23.91, 120.69),
    "TWCHA": (24.07, 120.54),
    "TWYUN": (23.71, 120.43),
    "TWCYQ": (23.48, 120.45),
    "TWTNN": (22.99, 120.21),
    "TWKHH": (22.62, 120.31),
    "TWPIF": (22.67, 120.49),
    "TWTTT": (22.75, 121.15),
    "TWHUA": (23.97, 121.60),
    "TWILA": (24.75, 121.75),
    "TWNWT": (25.01, 121.45),
    "TWKEE": (25.13, 121.74),
    "TWTPE": (25.05, 121.55),
    "TWCYI": (23.48, 120.45),
}

COUNTY_NAME = {
    "TWCHA": "彰化縣",
    "TWCYI": "嘉義市",
    "TWCYQ": "嘉義縣",
    "TWHSQ": "新竹縣",
    "TWHSZ": "新竹市",
    "TWHUA": "花蓮縣",
    "TWILA": "宜蘭縣",
    "TWKEE": "基隆市",
    "TWKHH": "高雄市",
    "TWKIN": "金門縣",
    "TWLIE": "媽祖群島",
    "TWMIA": "苗栗縣",
    "TWNAN": "南投縣",
    "TWNWT": "新北市",
    "TWPEN": "澎湖縣",
    "TWPIF": "屏東縣",
    "TWTAO": "桃園市",
    "TWTNN": "臺南市",
    "TWTPE": "臺北市",
    "TWTXG": "臺中市",
    "TWTTT": "臺東縣",
    "TWYUN": "雲林縣",
}
