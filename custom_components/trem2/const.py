"""Constants for the custom component."""

from datetime import UTC
from zoneinfo import ZoneInfo

from homeassistant.const import ATTR_LATITUDE, ATTR_LOCATION, ATTR_LONGITUDE, Platform
from aiohttp import ClientTimeout

# Initialize
DEFAULT_NAME = "TREM2"
DEFAULT_ICON = "mdi:waveform"
REPORT_ICON = "mdi:information-box"
DOMAIN = "trem2"
INT_DEFAULT_ICON = "mdi:circle-outline"
INT_TRIGGER_ICON = "mdi:alert-circle-outline"
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.IMAGE,
    Platform.SELECT,
    Platform.SENSOR,
]

# Config
CONF_AGREE = "agree_tos_20250523"
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
ZIP3_TOWN = {
    "100": "臺北市中正區",
    "103": "臺北市大同區",
    "104": "臺北市中山區",
    "105": "臺北市松山區",
    "106": "臺北市大安區",
    "108": "臺北市萬華區",
    "110": "臺北市信義區",
    "111": "臺北市士林區",
    "112": "臺北市北投區",
    "114": "臺北市內湖區",
    "115": "臺北市南港區",
    "116": "臺北市文山區",
    "200": "基隆市仁愛區",
    "201": "基隆市信義區",
    "202": "基隆市中正區",
    "203": "基隆市中山區",
    "204": "基隆市安樂區",
    "205": "基隆市暖暖區",
    "206": "基隆市七堵區",
    "207": "新北市萬里區",
    "208": "新北市金山區",
    "220": "新北市板橋區",
    "221": "新北市汐止區",
    "231": "新北市新店區",
    "234": "新北市永和區",
    "235": "新北市中和區",
    "236": "新北市土城區",
    "241": "新北市三重區",
    "242": "新北市新莊區",
    "260": "宜蘭縣宜蘭市",
    "261": "宜蘭縣頭城鎮",
    "300": "新竹市",
    "302": "新竹縣竹北市",
    "303": "新竹縣湖口鄉",
    "304": "新竹縣新豐鄉",
    "305": "新竹縣新埔鎮",
    "320": "桃園市中壢區",
    "324": "桃園市平鎮區",
    "325": "桃園市龍潭區",
    "326": "桃園市楊梅區",
    "327": "桃園市新屋區",
    "330": "桃園市桃園區",
    "333": "桃園市龜山區",
    "334": "桃園市八德區",
    "335": "桃園市大溪區",
    "350": "苗栗縣竹南鎮",
    "351": "苗栗縣頭份市",
    "360": "苗栗縣苗栗市",
    "400": "臺中市中區",
    "401": "臺中市東區",
    "402": "臺中市南區",
    "403": "臺中市西區",
    "404": "臺中市北區",
    "406": "臺中市北屯區",
    "407": "臺中市西屯區",
    "408": "臺中市南屯區",
    "500": "彰化縣彰化市",
    "600": "嘉義市",
    "630": "雲林縣斗南鎮",
    "632": "雲林縣虎尾鎮",
    "637": "雲林縣崙背鄉",
    "640": "雲林縣斗六市",
    "700": "臺南市中西區",
    "701": "臺南市東區",
    "702": "臺南市南區",
    "704": "臺南市北區",
    "708": "臺南市安平區",
    "800": "高雄市新興區",
    "801": "高雄市前金區",
    "802": "高雄市苓雅區",
    "803": "高雄市鹽埕區",
    "804": "高雄市鼓山區",
    "807": "高雄市三民區",
    "811": "高雄市楠梓區",
    "813": "高雄市左營區",
    "820": "高雄市岡山區",
    "830": "高雄市鳳山區",
    "880": "澎湖縣馬公市",
    "900": "屏東縣屏東市",
    "920": "屏東縣潮州鎮",
    "950": "臺東縣臺東市",
    "970": "花蓮縣花蓮市",
    "971": "花蓮縣新城鄉",
    "981": "花蓮縣玉里鎮",
    "890": "金門縣金沙鎮",
    "893": "金門縣金城鎮",
    "209": "連江縣南竿鄉",
    "210": "連江縣北竿鄉",
    "211": "連江縣莒光鄉",
    "212": "連江縣東引鄉",
    "290": "釣魚臺列嶼",
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
MANUFACTURER = "高家田 (jayx1011)"

# Stored
STORAGE_EEW = "{domain}/{entry_id}/recent_data.json"
STORAGE_REPORT = "{domain}/{entry_id}/report.json"

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
    "ws_taipei_1": "wss://lb-1.exptech.dev/websocket",
    "ws_pingtung_1": "wss://lb-2.exptech.dev/websocket",
    "ws_taipei_2": "wss://lb-3.exptech.dev/websocket",
    "ws_pingtung_2": "wss://lb-4.exptech.dev/websocket",
}
REPORT_URL = "https://api-1.exptech.dev/api/v2/eq/report"
LOGIN_URL = "https://api-1.exptech.dev/api/v3/et/login"
REQUEST_TIMEOUT = ClientTimeout(
    total=15,
    connect=10,
    sock_read=10,
    sock_connect=10,
)

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
