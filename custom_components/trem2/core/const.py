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

COUNTY_SITE_VALUES = {
    "TWKIN": 0.75,  # 金門縣
    "TWLIE": 0.7,  # 連江縣 (媽祖)
    "TWPEN": 0.8,  # 澎湖
    "TWTAO": 1.15,  # 桃園市
    "TWHSQ": 1.1,  # 新竹縣
    "TWHSZ": 1.1,  # 新竹市
    "TWMIA": 1.05,  # 苗栗縣
    "TWTXG": 1.0,  # 臺中市
    "TWNAN": 1.2,  # 南投縣
    "TWCHA": 0.95,  # 彰化縣
    "TWYUN": 0.9,  # 雲林縣
    "TWCYQ": 0.85,  # 嘉義縣
    "TWTNN": 0.95,  # 臺南市
    "TWKHH": 0.9,  # 高雄市
    "TWPIF": 0.9,  # 屏東縣
    "TWTTT": 1.25,  # 臺東縣
    "TWHUA": 1.3,  # 花蓮縣
    "TWILA": 1.3,  # 宜蘭縣
    "TWNWT": 1.1,  # 新北市
    "TWKEE": 1.15,  # 基隆市
    "TWTPE": 1.2,  # 臺北市
    "TWCYI": 0.85,  # 嘉義市
}

TAIWAN_CENTER = (23.97565, 120.9738819)  # 台灣中心點

COUNTY_CENTERS = {
    "TWKIN": (24.43, 118.32),  # 金門縣
    "TWLIE": (26.15, 119.92),  # 連江縣 (馬祖)
    "TWPEN": (23.57, 119.58),  # 澎湖
    "TWTAO": (24.99, 121.31),  # 桃園市
    "TWHSQ": (24.84, 121.01),  # 新竹縣
    "TWHSZ": (24.80, 120.97),  # 新竹市
    "TWMIA": (24.56, 120.82),  # 苗栗縣
    "TWTXG": (24.14, 120.68),  # 臺中市
    "TWNAN": (23.91, 120.69),  # 南投縣
    "TWCHA": (24.07, 120.54),  # 彰化縣
    "TWYUN": (23.71, 120.43),  # 雲林縣
    "TWCYQ": (23.48, 120.45),  # 嘉義縣
    "TWTNN": (22.99, 120.21),  # 臺南市
    "TWKHH": (22.62, 120.31),  # 高雄市
    "TWPIF": (22.67, 120.49),  # 屏東縣
    "TWTTT": (22.75, 121.15),  # 臺東縣
    "TWHUA": (23.97, 121.60),  # 花蓮縣
    "TWILA": (24.75, 121.75),  # 宜蘭縣
    "TWNWT": (25.01, 121.45),  # 新北市
    "TWKEE": (25.13, 121.74),  # 基隆市
    "TWTPE": (25.05, 121.55),  # 臺北市
    "TWCYI": (23.48, 120.45),  # 嘉義市
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

EARTH_RADIUS = 6371.008
