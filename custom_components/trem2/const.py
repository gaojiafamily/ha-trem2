"""Constants for the custom component."""

from datetime import UTC
from zoneinfo import ZoneInfo

from homeassistant.const import ATTR_LATITUDE, ATTR_LOCATION, ATTR_LONGITUDE

# Initialize
DEFAULT_NAME = "TREM2"
DEFAULT_ICON = "mdi:waveform"
DOMAIN = "trem2"
PLATFORMS = ["image", "sensor"]

# Config
CONF_PASS = "pass"
CONF_PROVIDER = "type"
PROVIDER_OPTIONS = [
    ("全部 (ALL)", ""),
    ("中央氣象署 (CWA)", "cwa"),
    ("日本防災科研 (NIED)", "nied"),
    ("日本氣象廳 (JMA)", "jma"),
    ("韓國氣象廳 (KMA)", "kma"),
    ("中國四川省地震局 (SCDZJ)", "scdzj"),
    ("中國福建省地震局 (FJDZJ)", "fjdzj"),
]
PARAMS_OPTIONS = [
    CONF_PROVIDER,
]
SOURCE_INIT = "init"

# Proj
CLIENT_NAME = "HA-TREM2"
PROJECT_URL = "https://github.com/gaojiafamily/ha-trem2"
ISSUE_URL = f"{PROJECT_URL}/issues"
OFFICIAL_URL = "https://www.gj-smart.com"

# Version
__version__ = "1.2.0"

# Timezone
TZ_TW = ZoneInfo("Asia/Taipei")
TZ_UTC = UTC

# General sensor attributes
ATTRIBUTION = "本訊息僅提供應變參考，因時效需求存在不準確性。"
ATTR_REPORT_IMG_URL = "report_img_url"
ATTR_API_NODE = "api_node"
ATTR_ID = "serial"
ATTR_AUTHOR = "provider"
ATTR_DEPTH = "depth"
ATTR_MAG = "magnitude"
ATTR_LIST = "list"
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
    ATTR_LONGITUDE,
    ATTR_LATITUDE,
    ATTR_DEPTH,
    ATTR_MAG,
    ATTR_LOCATION,
    ATTR_LIST,
    ATTR_TIME,
]
MANUFACTURER = "居智科技"

# Coordinator
UPDATE_COORDINATOR = "coordinator"
UPDATE_LISTENER = "update_listener"

# Stored
STORAGE_EEW = f"{DOMAIN}/recent_data.json"
STORAGE_REPORT = f"{DOMAIN}/report.json"

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
    "ws_taipei": "wss://lb-1.exptech.dev/websocket",
    "ws_pingtung": "wss://lb-2.exptech.dev/websocket",
    "ws_taipei_2": "wss://lb-3.exptech.dev/websocket",
    "ws_pingtung_2": "wss://lb-4.exptech.dev/websocket",
}
REPORT_URL = "https://api.exptech.dev/api/v2/eq/report"
REPORT_IMG_URL = "https://api-1.exptech.dev/file/images/report"
LOGIN_URL = "https://api-1.exptech.dev/api/v3/et/login"
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
