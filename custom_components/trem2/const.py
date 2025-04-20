"""Constants for the custom component."""

from datetime import UTC
from zoneinfo import ZoneInfo

# Initialize
CONF_NAME = "name"
DEFAULT_NAME = "TREM"
DEFAULT_ICON = "mdi:waveform"
DOMAIN = "trem2"
PLATFORMS = ["image", "sensor"]

# Proj
CLIENT_NAME = "HA-TREM2"
PROJECT_URL = "https://github.com/gaojiafamily/ha-trem2"
ISSUE_URL = f"{PROJECT_URL}/issues"
OFFICIAL_URL = "https://www.gj-smart.com"

# Version
__version__ = "1.1.2"

# Timezone
TZ_TW = ZoneInfo("Asia/Taipei")
TZ_UTC = UTC

# General sensor attributes
ATTRIBUTION = "本訊息僅提供應變參考，因時效需求存在不準確性。"
ATTR_SAVE2FILE = "filename"
ATTR_REPORT_IMG_URL = "report_img_url"
ATTR_API_URL = "api_url"
ATTR_API_NODE = "api_node"
ATTR_DATA = "data"
ATTR_ID = "serial"
ATTR_AUTHOR = "provider"
ATTR_LNG = "longitude"
ATTR_LAT = "latitude"
ATTR_DEPTH = "depth"
ATTR_MAG = "magnitude"
ATTR_LIST = "list"
ATTR_LOC = "location"
ATTR_TIME = "time_of_occurrence"
ATTR_COUNTY = {
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
NOTIFICATION_ATTR = [
    ATTR_ID,
    ATTR_AUTHOR,
    ATTR_LNG,
    ATTR_LAT,
    ATTR_DEPTH,
    ATTR_MAG,
    ATTR_LOC,
    ATTR_LIST,
    ATTR_TIME,
]
MANUFACTURER = "居智科技"

# Coordinator
TREM2_COORDINATOR = "trem2_coordinator"
TREM2_NAME = "trem2_name"
UPDATE_LISTENER = "update_listener"

# Stored
STORAGE_EEW = f"{DOMAIN}/recent_data.json"
STORAGE_REPORT = f"{DOMAIN}/report.json"
STORAGE_TOKEN = f"{DOMAIN}/token.json"

# REST
HA_USER_AGENT = "TREM custom integration for Home Assistant (https://github.com/gaojiafamily/ha-trem2)"
API_VERSION = 2
BASE_URLS = {
    "tainan": "https://api-1.exptech.dev",
    "taipei": "https://api-2.exptech.dev",
    "taipei_1": "https://lb-1.exptech.dev",
    "pingtung_1": "https://lb-2.exptech.dev",
    "taipei_2": "https://lb-3.exptech.dev",
    "pingtung_2": "https://lb-4.exptech.dev",
}
WS_URLS = {
    "taipei_1": "wss://lb-1.exptech.dev/websocket",
    "pingtung_1": "wss://lb-2.exptech.dev/websocket",
    "taipei_2": "wss://lb-3.exptech.dev/websocket",
    "pingtung_2": "wss://lb-4.exptech.dev/websocket",
}
REPORT_URL = "https://api.exptech.dev/api/v2/eq/report"
REPORT_IMG_URL = "https://api-1.exptech.dev/file/images/report"
REQUEST_TIMEOUT = 30  # seconds

# STRINGS
STARTUP = f"""

-------------------------------------------------------------------
{CLIENT_NAME}
Version: {__version__}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
