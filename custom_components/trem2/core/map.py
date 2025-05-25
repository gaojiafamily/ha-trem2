"""Drawing isoseismal map for Taiwan Real-time Earthquake Monitoring integration."""

from datetime import datetime
from io import BytesIO

from defusedxml import ElementTree as ET
from reportlab.graphics import renderSVG
import segno
from svglib.svglib import svg2rlg

from .const import (
    COUNTY_CENTERS,
    COUNTY_NAME,
    DEFAULT_COLOR,
    FOOT_NOTE,
    INTENSITY_COLORS,
    PROVIDERS,
    TAIWAN_CENTER,
    TZ_TW,
    TZ_UTC,
)
from .earthquake import intensity_to_text, round_intensity

TW_MAP_SVG = {
    "head": """
        <?xml version="1.0" encoding="UTF-8"?>
        <svg width="1000" height="1000" fill="#808080" stroke="#fff" baseProfile="tiny" xmlns="http://www.w3.org/2000/svg">
        <rect x="0" y="0" width="1000" height="1000" fill="#2D2926" opacity="1" />
    """,
    "TWKIN": '<path d="m181.2 423.5v0.1l-1.1-0.4-0.3-0.4 0.6-1.2-1.3-0.9-0.2-0.3-0.1-0.1-2.5-1.9-1.8-1.9-2.7 1-1.3 1.6 0.2 0.7-0.1 0.6-0.3 0.2-0.3-0.1-0.4 2.4-5 5.9-11.4-4.1 0.2 1-0.2 1-0.3 0.1 1.1 1.1-0.4 8.2-3.3 2.6 2.5 2.7-1.4-0.6-1.9-0.2-1.7-0.7-0.9-1.5 0.3-0.6 1.6-1.9 0.5-1 0.1-1.4v-1.8l-0.6-3.1-1.2-3-0.2-1.6 1.1-0.6 5.5-2.7 7.2 4.7 5-0.6 0.8-6.3 1.7-3.9 5.3-1.1 5.2 4.7 2 5.3zm0.2 10.5 0.3-2.1h0.3l-0.2 1.7-0.4 0.4zm0.9-5-1-3 0.1-0.7 0.3-0.4 0.8 2.4-0.2 1.7z" id="TWKIN" fill="{TWKIN_COLOR}"></path>',  # noqa: E501
    "TWLIE": '<path d="m181.2 423.5v0.1l-1.1-0.4-0.3-0.4 0.6-1.2-1.3-0.9-0.2-0.3-0.1-0.1-2.5-1.9-1.8-1.9-2.7 1-1.3 1.6 0.2 0.7-0.1 0.6-0.3 0.2-0.3-0.1-0.4 2.4-5 5.9-11.4-4.1 0.2 1-0.2 1-0.3 0.1 1.1 1.1-0.4 8.2-3.3 2.6 2.5 2.7-1.4-0.6-1.9-0.2-1.7-0.7-0.9-1.5 0.3-0.6 1.6-1.9 0.5-1 0.1-1.4v-1.8l-0.6-3.1-1.2-3-0.2-1.6 1.1-0.6 5.5-2.7 7.2 4.7 5-0.6 0.8-6.3 1.7-3.9 5.3-1.1 5.2 4.7 2 5.3zm0.2 10.5 0.3-2.1h0.3l-0.2 1.7-0.4 0.4zm0.9-5-1-3 0.1-0.7 0.3-0.4 0.8 2.4-0.2 1.7z" id="TWLIE" fill="{TWLIE_COLOR}"></path>',  # noqa: E501
    "TWPEN": '<path d="m409.7 611.6 0.9 2.9 -0.4 2.2 -1.4 -1.4 -1.9 -1.3 -2 -0.4 -2.8 1.6 -2.1 0.3 -1 0.5 -0.5 1.1 -0.8 2.9 -0.5 0.9 -3.4 2 -3.4 0.5 -3.5 -1.4 -3.5 -3.5 0.9 -1.8 1.9 2.3 2.3 2.9 0.6 3.1 -0.8 2.6 -2.1 -1.8 -0.7 -1.4 -0.8 -1.1 -1.2 -1 -1.6 -0.4 0.7 v 0.2 l -0.2 0.2 -0.7 0.4 -0.2 -2.9 0.2 -2.9 h 1.3 l 1.5 0.4 5.3 -3.4 3.4 -1.1 -0.9 3.2 -0.4 0.9 2.9 -0.9 2.2 0.3 1.6 -0.2 1.2 -1.9 3.4 6.2 z" id="TWPEN" fill="{TWPEN_COLOR}"></path>',  # noqa: E501
    "TWTAO": '<path d="m657.2 325.1 6.4-10.3 5-5.9 5.2-4.4 13.2-4.4 3.1-1.9 2.7-2.4 3.3-1.8 6.4-2.3 14.5-2.6 3 3.3 4.6 2.2 3.4 2.2 2.3 2.1 2.9 0.7 3.1 1.6 3.7 5.4 0.3 2.9-0.7 3-2.4 2.5-9.4 2.8-2.7 2.9 0.2 4.5-0.8 4.1 0.8 3.7 3.8 3.7 0.8 3.7-1 4.8 3.7 2.1 5.3-0.3 3.7 1.4 6 8.9-1 3.8-2.3 2.7 0.6 3.7 1 4.1 6.4 6 1.8 4-2.2 0.6-3.9 2.8 2.3 9-1.6 2.7-2.5 1-2.3-0.5-2.9 1.1-0.3 1.1-3.5-1.5-5.2-3-2.9-2.1-4-0.7-4.5-2.6-3.7-2.9-0.4-3.1 3.3-4.7 1.4-5.6-1.2-5.2-0.2-3.6-2.5-1.9-3.1-1.6-1.9-3.3-2.4-2.5-2.8 0.2-2.8-0.5-2.2-2.2-3-2.2-4.8-1.5-2.4-2.7 0.8-4.2-2.6-3-4.9-1.6-3-1.4-3.1-0.9-3.6-1.4-2.9-6.3-3.3-2.2-9.8 0.7-2.3-0.8z" id="TWTAO" fill="{TWTAO_COLOR}"></path>',  # noqa: E501
    "TWHSQ": '<path d="m657.2 325.1 2.3 0.8 9.8-0.7 3.3 2.2 2.9 6.3 3.6 1.4 3.1 0.9 3 1.4 4.9 1.6 2.6 3-0.8 4.2 2.4 2.7 4.8 1.5 3 2.2 2.2 2.2 2.8 0.5 2.8-0.2 2.4 2.5 1.9 3.3 3.1 1.6 2.5 1.9 0.2 3.6 1.2 5.2-1.4 5.6-3.3 4.7 0.4 3.1 3.7 2.9 4.5 2.6 4 0.7 2.9 2.1 5.2 3 3.5 1.5-1.7 4.7-1 3.4 0.4 3.2-2.7 4.2-10.1 10.2-3.1 7.5-2-0.5-7.7 0.7-0.5 0.4-0.5-3.5-3.3-5.6-2.3-2.4-1-3.1-3.6-2.9-9.1 2.3-3.4-0.4-4.9 0.4-5.5 1.5-3-0.7 0.7-3.7 0.9-3.3-0.7-2.9-0.7-2.1 0.7-2.3 0.5-2.4 0.3-2.8-0.6-3.8-2.7-2.4-8.8-4.2-4.3-3.2-2.8-3.2-3.2-8 1.8-2.2 1.6-4.1 2.5-3.1 4.2-1.7 3.7-0.6 1.7-1 0.7-2.7-1.3-2.6-2.8-2.8-3.9-2-10.9-3.5-6-2.6 0.1-0.1 1.1-1.6 0.4-2.7 0.6-2.1 1.5-2.1 1.9-1.6 1.8-0.6-0.1-0.9 0.5-2.1 1.6-4.4 1.5-2.3z" id="TWHSQ" fill="{TWHSQ_COLOR}"></path>',  # noqa: E501
    "TWHSZ": '<path d="m646.3 345.6 6 2.6 10.9 3.5 3.9 2 2.8 2.8 1.3 2.6-0.7 2.7-1.7 1-3.7 0.6-4.2 1.7-2.5 3.1-1.6 4.1-1.8 2.2-0.2 0.2-3.3 0.8-3.1-1.3-2-2.7-3-1.9-5-1.9 0.8-3 4-8.2 1.6-2.1 0.5-1.2v-1.2l-0.5-1.3-0.8-1.6 1.1-2.2 1.2-1.3z" id="TWHSZ" fill="{TWHSZ_COLOR}"></path>',  # noqa: E501
    "TWMIA": '<path d="m655 374.5 3.2 8 2.8 3.2 4.3 3.2 8.8 4.2 2.7 2.4 0.6 3.8-0.3 2.8-0.5 2.4-0.7 2.3 0.7 2.1 0.7 2.9-0.9 3.3-0.7 3.7 3 0.7 5.5-1.5 4.9-0.4 3.4 0.4 9.1-2.3 3.6 2.9 1 3.1 2.3 2.4 3.3 5.6 0.5 3.5-2.7 1.9-1.3 4-3.5 1.5-3.9-0.1-3 2.2-3.3 3.1-4.2 2.4-8.4 6.6-4.9 2-6.4 3.5-3.9-1.6-3.6-4-4.4-1.7-7.1-0.6-4 2.4-0.6 5.3-3.7 2-8.8 0.5-8.4-4.8-4.7-0.9-5.3-2.6-10.9-8-4.5-3.9-3.4-3.6-6.6-10.3 5.2-5.8 1.3-2.9 0.7-4.8 1.5-4 4.3-7.5 1.2-4.5 1.1-2 4.8-1.4 1.4-1.5 0.8-1.9 1-1.8 3-3.2 3.4-2.4 4-1.1 5.2 1-0.7-3.9 1.9-2.7 2.7-2.7 1.3-4.2 0.6-1.3 2.6-1.3 0.3-0.9 5 1.9 3 1.9 2 2.7 3.1 1.3 3.3-0.8 0.2-0.2z" id="TWMIA" fill="{TWMIA_COLOR}"></path>',  # noqa: E501
    "TWTXG": '<path d="M712.3 433.2l0.5-0.4 7.7-0.7 2 0.5 2.6 0.8-0.5 4 1.1 2.6 3.5 0.8 3.2 1.9 2.7 1.8 2.8-0.4 3.4-1.7 3.6 0 4.2 3.4-3.4 3.5-0.3 3-1.7 4.5-5.4 3.4-2.2 3.6-0.9 3.7-2.2 2.7-2.5 1.3-0.9 1.4-2 1.5-9.6-0.9-3.4-0.8-3.4 0.2-8 3.2-4.5 0.7-4.4 0.2-6.4 3.3-3.2 0.6-3.6 2.1-5.7 5.5-3.6 1.4-4.8-0.1-3.4 2.8-1.9 3.9-2.5 0.7-6.4-4.8-2.2 1.4-4.2 5.5-4.3 0.2-7.3-1.1-4.6 2.2-2.7 6.1-5.4 10.4-3.6 3.4-3 0.5-13-1.8-3-0.1-0.1-1-3.9-2.6-3.1-0.5-0.9-2.5 0-2.8-1.4-2.9-2.3-3.6-3.2-2.6-8.5-2.5-3.3-3.9-0.7-5.5-1.9-4.6-2.9-2.5-4.2-1.3 0.5-0.6 0.5-2.4 2.4-1.9 1.6-4.7 1.9-8.8 6.7-11.7 2.1-7.1 2.4-4 9.6-10.6 6.6 10.3 3.4 3.6 4.5 3.9 10.9 8 5.3 2.6 4.7 0.9 8.4 4.8 8.8-0.5 3.7-2 0.6-5.3 4-2.4 7.1 0.6 4.4 1.7 3.6 4 3.9 1.6 6.4-3.5 4.9-2 8.4-6.6 4.2-2.4 3.3-3.1 3-2.2 3.9 0.1 3.5-1.5 1.3-4 2.7-1.9z" id="TWTXG" fill="{TWTXG_COLOR}"></path>',  # noqa: E501
    "TWCHA": '<path d="m563.1 480.3 4.2 1.3 2.9 2.5 1.9 4.6 0.7 5.5 3.3 3.9 8.5 2.5 3.2 2.6 2.3 3.6 1.4 2.9v2.8l0.9 2.5 3.1 0.5 3.9 2.6 0.1 1v2.6l-3.1 1.1-0.9 2.1 0.4 2.9-1.4 3.3-1.2 3.9-0.1 4.1-0.8 4.7-0.7 9.7 1.5 4.5 2.6 2.4 2.8 1 4.1 2.1-0.7 2.5-2.8 1.1-1.8 1.7-1.7 1.1-0.7 0.5-8.7-1.7-4.2 0.1-8.7-4.4-14.2-1.6-8.4-3.2-4.8-1.3-5.4-0.3-15.9 1.9-5.5-3.2 0.6-1 1.1-5.1 0.9-2.1 5.1-4.9 1.5-2.1 1.9-5.6 3-5.6 4.2-11.6 1.9-3.3 2.2-2.2 1.8-1.2 1.5-0.8 1.2-1 0.4-2.2 0.9-2 3.7-2.9 0.8-2.2 0.4-7.2 0.7-2 1.9-1.9 8.2-9.5z" id="TWCHA" fill="{TWCHA_COLOR}"></path>',  # noqa: E501
    "TWYUN": '<path d="m519.2 556.7 5.5 3.2 15.9-1.9 5.4 0.3 4.8 1.3 8.4 3.2 14.2 1.6 8.7 4.4 4.2-0.1 8.7 1.7 0.7-0.5 1.4 5.2-1.5 3.4-0.7 5.2 0.7 5.5-1.3 3.7-0.7 4.2 2.8 3.4 4.2 1.8 4.9-1.5 6-0.6 1.9 2.5h-0.4l-0.3 3.6v2.5l-2.8 0.9-8.4 1.7-4.6 0.5-1.7-2.9-3.4-2.4-6 1.7-2.7 0.4-9.1-3.3-3.6-4.2-3.8-3.4-4.9 0.3-9.1 1.7-5.2 1.4-11.8 6.8-2.7 2.7-3.2 1.7-5 4.1-3.9 0.6-1.4 2.2-1.3 3.5-2.8 2.3-4.4-0.1-6-3.3-7.6 0.8-0.1 0.1h-0.7l3.4-3.7-0.2-11.8 0.5-8.9 2-7 3.2-5.6 0.9-7.2 1.7-6.3 0.9-2.2 4.4-5.8 0.7-2 0.6-1.1 4-3.1 0.6-1.2z" id="TWYUN" fill="{TWYUN_COLOR}"></path>',  # noqa: E501
    "TWCYQ": '<path d="m496.5 622.6h0.7l0.1-0.1 7.6-0.8 6 3.3 4.4 0.1 2.8-2.3 1.3-3.5 1.4-2.2 3.9-0.6 5-4.1 3.2-1.7 2.7-2.7 11.8-6.8 5.2-1.4 9.1-1.7 4.9-0.3 3.8 3.4 3.6 4.2 9.1 3.3 2.7-0.4 6-1.7 3.4 2.4 1.7 2.9 4.6-0.5 8.4-1.7 2.8-0.9v-2.5l0.3-3.6h0.4l4.4 0.5 4.8 1.9 3 0.8 3.7 2.1-0.3 3.8-2.1 3.7 0.9 3.4 1.9 4.7 0.3 4.2 0.8 2.8 5.5 1 18.4 0.1 0.6 0.2-13.3 6.8-6.1 4.8-2.5 4.9-3.1 3.7-5.5 3.1-5.8 4.4-3.2 3.8-8.9 5.3-4.2 0.4-4.9-0.5-2.6 2.6-0.1 3.5 1 3.3 0.7 4.8-6-0.7-2.7-0.8-3.6 0.5-3.8 1.7h-2.7l-3.3-2.5-1.1-3.3 1.2-10.3-0.7-5.4-7.1-7.3-1.3-3.6-1.5-3.1-2.9-1.7-5.1-1.7-6.1 0.3-11 2.1-5.6 2.5-4.4 3.3-3.4 3.4-4.8 3.7-4.1 2.6-1.8 3.6-4.5 2-5.3-1.3-6.3-1-3.8-1.4 2.8-0.2 2.3-1 1 0.3-0.6-2.3-1.6 1.2-1.3-0.4-1.8-0.1v-2.3l1.8-4.1 2.6-0.2h3.9l-2.6-7.5-3.1-5.8 1.4-2.6v-1.4l-2.2-1.1 0.3-1.2 1.3-1.5 0.6-1.9 3-3.8-6.2 0.4-0.2-6.3zm62.7 15.5 4.9-2 3.2-0.4 2.2-1.6-1.9-4.9-1.7-2.9-3-1.6-4-1.5-5.7 0.5-6.7 1.2-2.7 2.9 0.6 4.1 4.4 1.7 5.1 3.3 5.3 1.2zm-82.1-1.3 10.1-10.2 7.6-9.7 1.8-0.5-6.5 10.5-3.2 3.2-2.1 2.6-2.7 2.7-2.2 1.5-3.2 2.6-2.2 1.2 2.6-3.9z" id="TWCYQ" fill="{TWCYQ_COLOR}"></path>',  # noqa: E501
    "TWTNN": '<path d="m495.1 664.4 3.8 1.4 6.3 1 5.3 1.3 4.5-2 1.8-3.6 4.1-2.6 4.8-3.7 3.4-3.4 4.4-3.3 5.6-2.5 11-2.1 6.1-0.3 5.1 1.7 2.9 1.7 1.5 3.1 1.3 3.6 7.1 7.3 0.7 5.4-1.2 10.3 1.1 3.3 3.3 2.5h2.7l3.8-1.7 3.6-0.5 2.7 0.8 6 0.7-1.6 4.8-7.5 10.9-7.2 12.2-4.7 6-5.4 5.3-4.6 3.9-4.5 4.6-3.8 5.1-2.1 3.7-1.7 4-4.6 3.2-4.6 1.9-2.6 1.8-3 1.1-6.1-0.7-5.9 0.6-11.3-1.6-3.5-1.8-2.8-6.2-0.1-0.3-4.5 2.6-0.7-4.5-1.3-2.6-2.8-2.8 3.5-2.5 1.9-4.3-0.8-3.8-4.6-0.7-0.8 1.4-0.8 2.4-1.3 1.9-2.4-0.1-0.9-1.6 0.3-5-0.5-1.8-3-1.3-1.6 1.5-1.4 2.1-1.9 0.5-2.1-1.8-0.6-2.5 0.5-2.4 0.9-1.7 2.1-1.1 2.7-0.4 2.2-0.7 0.7-2.2-1-1.1-6.7-1.7v-1.4h5.6l-0.5-1.9-3.1-2.7-2-2.3 0.5-2.9 1.8-1 1.9-0.7 1-1.8-0.6-2.8-1-2.3 0.7-2.2 1-2.6 1.6-1.9-0.3-1.7 0.3-1.6 2.4-6.5 1.2-1.2 1.8-0.5-2.7-1.8 1.2-2.9z" id="TWTNN" fill="{TWTNN_COLOR}"></path>',  # noqa: E501
    "TWKHH": '<path d="M596.8 682.8l-0.7-4.8-1-3.3 0.1-3.5 2.6-2.6 4.9 0.5 4.2-0.4 8.9-5.3 3.2-3.8 5.8-4.4 5.5-3.1 3.1-3.7 2.5-4.9 6.1-4.8 13.3-6.8 3.2 0.7 4.2 1.6 3 4.2 0.5 1.5 1.4 4.2-2.2 3.5-4 1.8-1 2.3 0.7 2.9 4 2.6 4.6 3.7 2 5.5 0.2 1.8-11.2 2.8-4.7 2.9-2.9 2.8-5.6 3.7-0.6 4.1 1.6 4.3-1.9 3.5-5.3 2.9-0.7 5 1.6 7.1-2.2 9.5 0 8.1-3.1 4.2-6.2 5.3-1.7 7 1 5.9 2.2 3.3 4.4 4.6 0.9 3.5-2.8 0.4-3.8-0.7-3.1 0.2-6.1 4.8-4.3-4-5.4-6.4-5.2 1.3-4.8 4.3-9.4-4.8-6.8 3.2-4.6 5.1-5.7 2.1-12.9-0.8-1.3 3.5-0.9 5.2-1.9 5.7 0.4 5-0.1 6.9-4 15.3-0.2 5.1 2 5.4 0.3 5.9-5.8 14.8-1.9-0.8-1.1 0-1.4 0.5-1.5 0.1-9.4-7.4-8.8-12.4 9.2 11.1-1-5.2-1.6-2.9-1.2-2.3-3.8-4.4-6.5-6-2.5-3.1-1.2-3.4 1.6-3.3 0.8-3-1.1-4.1-1.9-4.1-3.6-5.5-3.3-7.4-0.7-3.3 0-2.1 1.1-2.6 0.3-1.7-0.4-0.9-1-0.7-0.9-0.9-0.4-1.7-2.1-3.5-0.5-1.4-1.6-9.9 4.5-2.6 0.1 0.3 2.8 6.2 3.5 1.8 11.3 1.6 5.9-0.6 6.1 0.7 3-1.1 2.6-1.8 4.6-1.9 4.6-3.2 1.7-4 2.1-3.7 3.8-5.1 4.5-4.6 4.6-3.9 5.4-5.3 4.7-6 7.2-12.2 7.5-10.9 1.6-4.8z" id="TWKHH" fill="{TWKHH_COLOR}"></path>',  # noqa: E501
    "TWPIF": '<path d="M551.1 836.2l5.8-14.8-0.3-5.9-2-5.4 0.2-5.1 4-15.3 0.1-6.9-0.4-5 1.9-5.7 0.9-5.2 1.3-3.5 12.9 0.8 5.7-2.1 4.6-5.1 6.8-3.2 9.4 4.8 4.8-4.3 5.2-1.3 5.4 6.4 4.3 4 6.1-4.8 3.1-0.2 3.8 0.7 2.5 4.7 0.5 3.5 3.9 1 4 2.6-2 9.9-0.1 3.8-1.5 3.5-7 3-3.5 2-5.5 1.2-3.9 3.2-1.7 4.7-2.6 4.8-2.2 5.4-0.6 10.6 0.9 4.7 1.4 4.4 0.8 5.1 0 3.8 1.9 3.7 3.3 4-1.8 2.7-3.8 2.3-1.5 2.8-0.4 3.3 2 2.8 2.4 1.2 2.3 3.2-0.1 4.1 0.4 4.4 2.3 4.3 3.3 3.5 7.4 3.4 3.2-0.3 0.6 37.2-1.1 5.3-1.8 4.3-2.4 1.8-2.9 2.7 0.1 6 1 6.6-0.2 4.2-3.3-4.9-4.9-3.7-5.7-2.5-5.7-1.4-0.2 4.7-1.7 1.7-2.4-0.6-2.7-2.2-0.1-1.7 0.9-5-4-6.7-0.3-1.8 0-1.4 0.3-2.4 0-7.7 0.4-2.3 1.8-2.5 0.4-2.2-14.4-37.2-1.1-2.1-4-4.9-3.2-7.1-1.4-2.1-5.9-4.6-2.3-1.3-0.8-0.3-0.8-0.6-0.7-2.6-0.5-1-3.1-2.1-7.3-3.4-3.2-2.3-3.5-3-1.6-1-0.2-0.1z" id="TWPIF" fill="{TWPIF_COLOR}"></path>',  # noqa: E501
    "TWTTT": '<path d="M634.7 759.1l2.8-0.4-0.9-3.5-4.4-4.6-2.2-3.3-1-5.9 1.7-7 6.2-5.3 3.1-4.2 0-8.1 2.2-9.5-1.6-7.1 0.7-5 5.3-2.9 1.9-3.5-1.6-4.3 0.6-4.1 5.6-3.7 2.9-2.8 4.7-2.9 11.2-2.8 0.8 5.3 3.7 5.9 5.6 2 4.4 2.1 3.6 3.4 4.5 0.7 4.1 1.1 6.6 11.5 8.5 7 5.9 0.8 4.7-2.7 0.6-4.4 0-4.9 2.2-4.3 3.5-9.6 2.6-5.5 1.8-6.1 1.9-4.8 2.5-3.7 2.6-5-0.4-4.9-1.3-5 2.8-3.9 7.8-3.8 2.5 0.8-3.3 19-1.6 3.5-5.1 6.8-1.9 3.5-1.5 4.4-1 8.3 0.1 7.3-0.8 6.9-3.5 7.2-1.5 1.6-3.4 2.5-1.5 1.6-0.8 1.6-1.2 4.2-3.5 6.1-2.1 9.4-1.5 4.2-7.4 10.7-0.9 2-10 8.4-2.4 2.8-0.4 1.9 0.5 4.5-0.1 2-0.9 2.3-1.6 2.6-3.4 4.3-3.4 3.2-11.6 7.8-7.8 8.5-1.9 1-1.5 2-3.8 9.7-1.8 3.6-5.8 7.3-2.4 4.3-1.3 8.8-3.5 12.1-6.9 12.1-1 4.1-1.2 11.6 0.2 10.5-3.2 0.3-7.4-3.4-3.3-3.5-2.3-4.3-0.4-4.4 0.1-4.1-2.3-3.2-2.4-1.2-2-2.8 0.4-3.3 1.5-2.8 3.8-2.3 1.8-2.7-3.3-4-1.9-3.7 0-3.8-0.8-5.1-1.4-4.4-0.9-4.7 0.6-10.6 2.2-5.4 2.6-4.8 1.7-4.7 3.9-3.2 5.5-1.2 3.5-2 7-3 1.5-3.5 0.1-3.8 2-9.9-4-2.6-3.9-1-0.5-3.5-2.5-4.7z m134.6 166.8l3.3 2.6 1.5 1.7-0.2 2-3.9 1.3-5.3-2.2-4.9-3.4-2.8-2.7 0.8-1.9 0-1.9-0.7-1.6-1.3-1.5 14.1 0 0 1.2-0.4 0.8-0.6 1.7-0.2 2.1 0.6 1.8z m-19.5-125.9l-1-3 0.4-0.4 7.3-0.6 0.8 0.5 0.5 1.4-0.6 2.8-0.6 1.2-0.3 1.2 0.3 1.1-0.1 0.8-0.5-0.1-1.3 0-0.6-0.2-0.3-0.4-1.9-0.7-2.1-3.6z" id="TWTTT" fill="{TWTTT_COLOR}"></path>',  # noqa: E501
    "TWHUA": '<path d="M727.6 474.4l2-1.5 0.9-1.4 2.5-1.3 2.2-2.7 0.9-3.7 2.2-3.6 5.4-3.4 1.7-4.5 0.3-3 3.4-3.5 1.8 1.5 4.7 2.2 10.8 2.8 6 2.3 4.7 0 3.5-3.3 1.7-4.3 2.7-0.6 13.4 7.9 8 1.3 0.8 0 0.5 0.5 0.6 1.1 0.5 1.1 0.2 0.7-1 1.7-4.2 4.1-4.6 6.3-3.3 2.7-1 1.4 0.5 1.5-0.6 1.1-4.9 3.6-1.8 1.8-2 4.3-2 8.8-5.4 7.8-1.1 3.2 0.2 3.4 1.3 3.8 1.1 1.6 0.9 0.7 0.6 1 0.1 2.3-0.8 2.7-2.7 4.1-0.5 2.5-0.3 4.6-2.3 11.7-4.6 12.4-5.8 28.8-3.4 7.1-8 46.2-2.5-0.8-7.8 3.8-2.8 3.9 1.3 5 0.4 4.9-2.6 5-2.5 3.7-1.9 4.8-1.8 6.1-2.6 5.5-3.5 9.6-2.2 4.3 0 4.9-0.6 4.4-4.7 2.7-5.9-0.8-8.5-7-6.6-11.5-4.1-1.1-4.5-0.7-3.6-3.4-4.4-2.1-5.6-2-3.7-5.9-0.8-5.3-0.2-1.8-2-5.5-4.6-3.7-4-2.6-0.7-2.9 1-2.3 4-1.8 2.2-3.5-1.4-4.2 4.3-2.5 2.2-2.1-1.2-4.4 1.1-1.9 1.1-3 3.7-2.7 5.4-1.2 5.3-0.2 3.8-3.4 1-6.2 2.8-3.7 5.5-2 3.3-2.3 1.1-3.6 2.3-9.1 0.9-6-0.7-5.2-0.8-3.9-2.3-2.9-1.5-2.9 4.1-6.8 0.1-2.7 1.8-5.1 2.8-6.1 2.2-6.3 1.1-7.2 0.5-5.4-1.3-3.2-1.5-2.4 1.7-5.5 3.7-7.7 5.8-7.6 0.1-2.7-1-3.3-3.8-2.4-2-2.2-0.2-7.2 2.7-2.1 4.7-1.6 3.8-1.7-0.2-2.6-1-4.5z" id="TWHUA" fill="{TWHUA_COLOR}"></path>',  # noqa: E501
    "TWILA": '<path d="M740.7 399.4l0.3-1.1 2.9-1.1 2.3 0.5 2.5-1 1.6-2.7-2.3-9 3.9-2.8 2.2-0.6 4.2-1.2 3.5-1.3 2.7-2.4 3.6-2.5 4.8-2.3 2.8-2-0.3-1.4-0.7-2.3-0.1-3 1.4-3.6 3.4-2.9 2.7-1.6 9.4-3.8 9.7-5.9 4.5-1.3 3.6-2.6 2.3-3.7 2.3-2.9 2.7-1.4 2.5-0.9 3.3-2.1 1.2-2.8-1.8-2.5 1-2.2 8.1-1.6 2.6-1.8 6-3.2 4.3-0.9 2.4 1.4 0.6 0.8-8.6 4.3-4 3.4-13.5 16.4-2.1 3.5-1.7 4.8-1.1 5.6-0.4 5.5 0.2 5.3 2.4 11.2-0.2 2.9-1 2.8 0.2 5.8 2.4 4.5 4.7 2.9 5.5 1.1 0 1.2-2.3-0.2-2.2 0.2-1.9 0.6-1.3 1 1.9 3.6 0.9 4.7-0.6 4.1-4.3 2.4-0.3 1.8 0.6 2.1 1.2 2 0.4 2-1.8 1.7-4.5 2.6-5 5.8-0.2 2.3 0.3 5-0.8 2-1 1.6-0.6 2.3-0.3 4.6-0.4 1.2-0.7 0.9-0.4 1 0.7 1.2 0.2 0.2-0.8 0-8-1.3-13.4-7.9-2.7 0.6-1.7 4.3-3.5 3.3-4.7 0-6-2.3-10.8-2.8-4.7-2.2-1.8-1.5-4.2-3.4-3.6 0-3.4 1.7-2.8 0.4-2.7-1.8-3.2-1.9-3.5-0.8-1.1-2.6 0.5-4-2.6-0.8 3.1-7.5 10.1-10.2 2.7-4.2-0.4-3.2 1-3.4 1.7-4.7z" id="TWILA" fill="{TWILA_COLOR}"></path>',  # noqa: E501
    "TWNWT": '<path d="M754.1 381.6l-1.8-4-6.4-6-1-4.1-0.6-3.7 2.3-2.7 1-3.8-6-8.9-3.7-1.4-5.3 0.3-3.7-2.1 1-4.8-0.8-3.7-3.8-3.7-0.8-3.7 0.8-4.1-0.2-4.5 2.7-2.9 9.4-2.8 2.4-2.5 0.7-3-0.3-2.9-3.7-5.4-3.1-1.6-2.9-0.7-2.3-2.1-3.4-2.2-4.6-2.2-3-3.3 8.1-1.5 3.4-1.3 4.5-3.7 1.3-0.7 1.6-0.3 2.2 0 2.6 0.8 1.3 1.9 0.9 2 1.1 1.1 2.5-1-2.6-4.1-4.2-4.2-2.2-1.4 0.7-1.9 1.3-1.1 1.3-0.7 0.6-0.6 1.5-3.8 2.3-4.2 4.7-4.3 7-3.5 7.9-1.8 7.8 0.9 3.2 2.5 7.3 10.1 2.5 5.4 0.9-0.3 1.9-0.6 2.3-0.2 1.5 0.4-0.1 0.7-0.7 0.9-0.7 1.3 0 1.5 0.8 0.9 1.6 1.2-3.1 2.1-5.2 2.3-2.3 1.5 0.4 2.1 2.1 2.7 1.2 2.5 2.1 2.5 2.6 2.5 2.2 1.6 7.6 3.1 3.7 0.5 2.9-1.1 1.8-1.3 0.3-1.8-2.7-2.8-0.1-2.2 0.2-8.6 24.9 6.1 2.4 1.5-1.2 2.6-0.3 2.1 0.5 3.8 1.7 6.2 1.9 3 1.6 0.7 5-0.8 2.6 0.3 3 0.8 2.7 1.3 1.5 1.9-6.3 3.1-0.6-0.8-2.4-1.4-4.3 0.9-6 3.2-2.6 1.8-8.1 1.6-1 2.2 1.8 2.5-1.2 2.8-3.3 2.1-2.5 0.9-2.7 1.4-2.3 2.9-2.3 3.7-3.6 2.6-4.5 1.3-9.7 5.9-9.4 3.8-2.7 1.6-3.4 2.9-1.4 3.6 0.1 3 0.7 2.3 0.3 1.4-2.8 2-4.8 2.3-3.6 2.5-2.7 2.4-3.5 1.3-4.2 1.2z m22.7-60.5l3-1.2 5.5-7 1.4-3-2.7-2.3-3.3-1.9-0.1-3.6 1.1-4.8-1.1-3.2-2.8-2.5-1.8-7.2-1.2-2.6-1.1-2.4-0.3-2.4 0.4-2.6-1.5-1.6-2.8-0.9-2.9 1.4-2.1 1.8-7.8 4.7-2.6 2.9-1.5 3.3-1.3 1.7-1.2 2.1 2.7 3.1 4.2 4 0.8 4.5-1.1 5.3 2.9 4.9 4.1 3.2 2.8 3.2 2.6 2.3 3.5 0.8 4.2 0z" id="TWNWT" fill="{TWNWT_COLOR}"></path>',  # noqa: E501
    "TWKEE": '<path d="M806.8 285.1l-0.2 8.6 0.1 2.2 2.7 2.8-0.3 1.8-1.8 1.3-2.9 1.1-3.7-0.5-7.6-3.1-2.2-1.6-2.6-2.5-2.1-2.5-1.2-2.5-2.1-2.7-0.4-2.1 2.3-1.5 5.2-2.3 3.1-2.1 1.1 0.7 0.5 0.8 1.2 1.1 2.8 1.1 8.1 1.9z" id="TWKEE" fill="{TWKEE_COLOR}"></path>',  # noqa: E501
    "TWNAN": '<path d="M599.5 519.1l3 0.1 13 1.8 3-0.5 3.6-3.4 5.4-10.4 2.7-6.1 4.6-2.2 7.3 1.1 4.3-0.2 4.2-5.5 2.2-1.4 6.4 4.8 2.5-0.7 1.9-3.9 3.4-2.8 4.8 0.1 3.6-1.4 5.7-5.5 3.6-2.1 3.2-0.6 6.4-3.3 4.4-0.2 4.5-0.7 8-3.2 3.4-0.2 3.4 0.8 9.6 0.9 1 4.5 0.2 2.6-3.8 1.7-4.7 1.6-2.7 2.1 0.2 7.2 2 2.2 3.8 2.4 1 3.3-0.1 2.7-5.8 7.6-3.7 7.7-1.7 5.5 1.5 2.4 1.3 3.2-0.5 5.4-1.1 7.2-2.2 6.3-2.8 6.1-1.8 5.1-0.1 2.7-4.1 6.8 1.5 2.9 2.3 2.9 0.8 3.9 0.7 5.2-0.9 6-2.3 9.1-1.1 3.6-3.3 2.3-5.5 2-2.8 3.7-1 6.2-3.8 3.4-5.3 0.2-5.4 1.2-3.7 2.7-1.1 3-1.1 1.9 1.2 4.4-2.2 2.1-4.3 2.5-0.5-1.5-3-4.2-4.2-1.6-3.2-0.7-0.6-0.2-18.4-0.1-5.5-1-0.8-2.8-0.3-4.2-1.9-4.7-0.9-3.4 2.1-3.7 0.3-3.8-3.7-2.1-3-0.8-4.8-1.9-4.4-0.5-1.9-2.5-6 0.6-4.9 1.5-4.2-1.8-2.8-3.4 0.7-4.2 1.3-3.7-0.7-5.5 0.7-5.2 1.5-3.4-1.4-5.2 1.7-1.1 1.8-1.7 2.8-1.1 0.7-2.5-4.1-2.1-2.8-1-2.6-2.4-1.5-4.5 0.7-9.7 0.8-4.7 0.1-4.1 1.2-3.9 1.4-3.3-0.4-2.9 0.9-2.1 3.1-1.1 0-2.6z" id="TWNAN" fill="{TWNAN_COLOR}"></path>',  # noqa: E501
    "TWTPE": '<path d="M776.8 321.1l-4.2 0-3.5-0.8-2.6-2.3-2.8-3.2-4.1-3.2-2.9-4.9 1.1-5.3-0.8-4.5-4.2-4-2.7-3.1 1.2-2.1 1.3-1.7 1.5-3.3 2.6-2.9 7.8-4.7 2.1-1.8 2.9-1.4 2.8 0.9 1.5 1.6-0.4 2.6 0.3 2.4 1.1 2.4 1.2 2.6 1.8 7.2 2.8 2.5 1.1 3.2-1.1 4.8 0.1 3.6 3.3 1.9 2.7 2.3-1.4 3-5.5 7-3 1.2z" id="TWTPE" fill="{TWTPE_COLOR}"></path>',  # noqa: E501
    "TWCYI": '<path d="M559.2 638.1l-5.3-1.2-5.1-3.3-4.4-1.7-0.6-4.1 2.7-2.9 6.7-1.2 5.7-0.5 4 1.5 3 1.6 1.7 2.9 1.9 4.9-2.2 1.6-3.2 0.4-4.9 2z" id="TWCYI" fill="{TWCYI_COLOR}"></path>',  # noqa: E501
    "qrcode": """
        <g id="qrcode" transform="translate(870 10)">
          <rect width="120" height="120" fill="#fff" />
          <g transform="scale(0.27) translate(-27, -27)">{qr_code}</g>
        </g>
    """,
    "info": """
        <g id="information" transform="translate(10, 10)" font-family="Noto Sans TC, sans-serif" font-size="16px" fill="#fff" opacity="1">
          <rect width="300" height="390" fill="#2e364f" opacity="0.6" stroke-width="2" />
          <text x="150" y="50" fill="#f0f0f0" stroke="none" font-size="24px" text-anchor="middle" opacity="1">詳細資訊</text>
          <g transform="translate(20, 80)" stroke="none"><path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z" />
            <text x="30" y="18" fill="#eedaf2" font-size="20px">{eq_id}</text></g>
          <g transform="translate(20, 120)" stroke="none"><path d="M12,11.5A2.5,2.5 0 0,1 9.5,9A2.5,2.5 0 0,1 12,6.5A2.5,2.5 0 0,1 14.5,9A2.5,2.5 0 0,1 12,11.5M12,2A7,7 0 0,0 5,9C5,14.25 12,22 12,22C12,22 19,14.25 19,9A7,7 0 0,0 12,2Z" />
            <text x="30" y="10" fill="#eedaf2"><tspan>{loc_main}</tspan><tspan x="30" dy="18">({loc_spec})</tspan></text>
          </g>
          <g transform="translate(20, 170)" stroke="none"><path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M16.2,16.2L11,13V7H12.5V12.2L17,14.9L16.2,16.2Z" />
            <text x="30" y="10"><tspan>發震時間 (UTC+8)</tspan><tspan x="30" dy="20" fill="#eedaf2" font-size="20px">{time}</tspan></text>
          </g>
          <g transform="translate(20, 220)" stroke="none"><path d="M5.41,21L6.12,17H2.12L2.47,15H6.47L7.53,9H3.53L3.88,7H7.88L8.59,3H10.59L9.88,7H15.88L16.59,3H18.59L17.88,7H21.88L21.53,9H17.53L16.47,15H20.47L20.12,17H16.12L15.41,21H13.41L14.12,17H8.12L7.41,21H5.41M9.53,9L8.47,15H14.47L15.53,9H9.53Z" />
            <text x="30" y="10"><tspan>最大震度</tspan><tspan x="30" dy="20" fill="#eedaf2" font-size="20px">{max_intensity}</tspan></text>
          </g>
          <g transform="translate(20, 270)" stroke="none"><path d="M22 12L20 13L19 14L18 13L17 16L16 13L15 21L14 13L13 15L12 13L11 17L10 13L9 22L8 13L7 19L6 13L5 14L4 13L2 12L4 11L5 10L6 11L7 5L8 11L9 2L10 11L11 7L12 11L13 9L14 11L15 3L16 11L17 8L18 11L19 10L20 11L22 12Z" />
            <text x="30" y="10"><tspan>芮氏規模</tspan><tspan x="30" dy="20" fill="#eedaf2" font-size="20px"><tspan>M</tspan><tspan x="50" font-size="12px">L</tspan><tspan> {mag}</tspan></tspan></text>
          </g>
          <g transform="translate(20, 320)" stroke="none"><path d="M16.59,5.59L18,7L12,13L6,7L7.41,5.59L12,10.17L16.59,5.59M16.59,11.59L18,13L12,19L6,13L7.41,11.59L12,16.17L16.59,11.59Z" />
            <text x="30" y="10"><tspan>震源深度</tspan><tspan x="30" dy="20" fill="#eedaf2" font-size="20px">{depth} 公里</tspan></text>
          </g>
          <text x="150" y="380" fill="#f0f0f0" stroke="none" font-size="14px" text-anchor="middle" opacity="1">{foot_note}</text>
        </g>
    """,  # noqa: E501
    "legend": """
        <g id="legend" transform="translate(10, 900)" font-family="Noto Sans TC, sans-serif">
          <rect x="0" y="-240" width="80" height="270" fill="#000"/>
          <rect x="10" y="5" width="20" height="20" fill="#387FFF"/><text x="40" y="15.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">1級</text>
          <rect x="10" y="-25" width="20" height="20" fill="#244FD0"/><text x="40" y="-15.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">2級</text>
          <rect x="10" y="-55" width="20" height="20" fill="#35BF56"/><text x="40" y="-45.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">3級</text>
          <rect x="10" y="-85" width="20" height="20" fill="#F8F755"/><text x="40" y="-75.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">4級</text>
          <rect x="10" y="-115" width="20" height="20" fill="#FFC759"/><text x="40" y="-105.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">5弱</text>
          <rect x="10" y="-145" width="20" height="20" fill="#FF9935"/><text x="40" y="-135.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">5強</text>
          <rect x="10" y="-175" width="20" height="20" fill="#DF443B"/><text x="40" y="-165.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">6弱</text>
          <rect x="10" y="-205" width="20" height="20" fill="#7B170F"/><text x="40" y="-195.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">6強</text>
          <rect x="10" y="-235" width="20" height="20" fill="#7237C1"/><text x="40" y="-225.0" fill="#fff" stroke="none" font-size="14" alignment-baseline="middle">7級</text>
        </g>
    """,  # noqa: E501
    "copyright": """
        <g id="copyright" transform="translate(0 960)" font-family="Noto Sans TC, sans-serif">
          <rect width="100%" height="40" fill="#000"/>
          <text x="500" y="15" fill="#fff" font-size="12" stroke="none" text-anchor="middle">HA-TREM2 | ©探索科技, ©高家田(jayx1011)</text>
          <text x="500" y="30" fill="#fff" font-size="12" stroke="none" text-anchor="middle">Taiwan Map Data Provided by SimpleMaps</text>
        </g>
    """,  # noqa: E501
    "end": "</svg>",
}

OFFSHORE_ZONES = {
    "Pacific Ocean": '<rect x="950" y="0" width="50" height="1000" fill="red" opacity="0.3"></rect>',
    "Taiwan Strait": '<rect x="0" y="0" width="50" height="1000" fill="red" opacity="0.3"></rect>',
    "East China Sea": '<rect x="0" y="0" width="1000" height="50" fill="red" opacity="0.3"></rect>',
    "Bashi Channel": '<rect x="900" y="900" width="100" height="100" fill="red" opacity="0.3"></rect>',
    "Sea": """
        <rect x="25" y="0" width="950" height="25" fill="red" opacity="0.3" stroke="none"/>
        <rect x="0" y="0" width="25" height="935" fill="red" opacity="0.3" stroke="none"/>
        <rect x="975" y="0" width="25" height="935" fill="red" opacity="0.3" stroke="none"/>
        <rect x="0" y="935" width="1000" height="25" fill="red" opacity="0.3" stroke="none"/>
    """,
}


def latlon_to_svg(
    epicenter_latlong,
    center_latlong=TAIWAN_CENTER,
    center_xy=(658.6, 552),
    viewbox=(1000, 1000),
):
    """Convert latitude and longitude to SVG coordinates.

    Parameters
    ----------
    epicenter_latlong : Tuple[float, float]
        Required latitude and longitude of the epicenter.
        Format: (latitude, longitude).

    center_latlong : Tuple[float, float]
        The latitude and longitude of the center point used as a reference.
        Format: (latitude, longitude).

    center_xy : Tuple[float, float]
        The SVG coordinate corresponding to the center_latlong.
        Format: (x, y).

    viewbox : Tuple[float, float]
        The dimensions of the SVG viewbox. This defines the width and height
        of the SVG canvas in pixels.
        Format: (width, height).

    Returns
    -------
    xy : Tuple[float, float]
        The calculated SVG coordinates corresponding to the input latitude
        and longitude.
        Format: (x, y).

    Examples
    --------
    >>> latlon_to_svg(
            epicenter_latlong=(23.5, 120.9),
            center_latlong=(23.97565, 120.9738819),
            center_xy=(658.6, 552),
            viewbox=(1000.0, 1000.0)
        )
    (646.2863500000018, 619.9500000000003)

    """
    # Latlong bounds for Taiwan
    min_lon, max_lon = 117, 124
    min_lat, max_lat = 20, 26

    # Calculate the pixel per degree
    pixels_per = (
        viewbox[0] / (max_lon - min_lon),
        viewbox[1] / (max_lat - min_lat),
    )

    # Calculate the difference from the center
    delta = (
        epicenter_latlong[0] - center_latlong[0],
        epicenter_latlong[1] - center_latlong[1],
    )

    # Convert to SVG coordinates
    xy = (
        center_xy[0] + delta[1] * pixels_per[1],
        center_xy[1] - delta[0] * pixels_per[0],
    )

    return max(0, min(xy[0], viewbox[0])), max(0, min(xy[1], viewbox[1]))


def is_offshore(latlong: tuple[float, float]) -> str | None:
    """Check if the epicenter is offshore."""
    lat, lon = latlong
    is_taiwan_mainland = (
        (118 <= lon <= 122 and 21.5 <= lat <= 25.5)
        or (119 <= lon <= 119.8 and 23 <= lat <= 23.8)
        or (118 <= lon <= 118.5 and 24 <= lat <= 24.5)
        or (119.8 <= lon <= 120.5 and 26 <= lat <= 26.5)
    )
    if is_taiwan_mainland:
        return None  # 臺灣本島

    match (lat, lon):
        case (lat, lon) if lat > 25.5:
            return "East China Sea"  # 東海
        case (lat, lon) if lon > 122:
            return "Pacific Ocean"  # 太平洋
        case (lat, lon) if lon < 118:
            return "Taiwan Strait"  # 台灣海峽
        case (lat, lon) if 121 <= lon <= 122 and 21.5 <= lat <= 22.5:
            return "Bashi Channel"  # 巴士海峽
        case _:
            return "Sea"  # 外海


def mag_to_intensity(mag):
    """Convert magnitude to intensity level."""
    if mag < 0:
        return 0
    if mag < 4.5:
        return round(mag)
    if mag < 5:
        return 5
    if mag < 5.5:
        return 6
    if mag < 6:
        return 7
    if mag < 6.5:
        return 8

    return 9


def generate_qr_code(url, bg_svg, scale=9):
    """Generate a QR code and overlay it on a background SVG.

    Parameters
    ----------
    url : str
        The text required to generate the QR code.
        Format: String.

    bg_svg : str | path
        `path` can be a file, a file-like, or a file path as str or pathlib.Path.
        Format: File path as str or pathlib.Path.

    scale : int | float
        indicating the size of a single module.
        Format: Integer or float.

    Examples
    --------
    >>> generate_qr_code(
            url="https://www.gj-smart.com/",
            bg_svg="/path/to/background.svg",
            scale=9
        )
    '<g id="qrcode" transform="translate(870 10)">...</g>'

    """
    qrcode = segno.make(
        url,
        error="h",
    )

    # Convert QR code to ByteIO object
    qr_svg = BytesIO()
    qrcode.save(qr_svg, scale=scale, kind="svg")
    qr_svg.seek(0)

    # Using svglib to convert SVG to drawing
    bg_drawing = svg2rlg(bg_svg)
    qr_drawing = svg2rlg(qr_svg)

    element = None
    if bg_drawing and qr_drawing:
        # Get the background dimensions
        bg_width = bg_drawing.width
        bg_height = bg_drawing.height

        # Get the QR Code dimensions
        qr_width = qr_drawing.width
        qr_height = qr_drawing.height

        # Calculate the position to center the QR Code
        x_offset = (bg_width - qr_width) / 2
        y_offset = (bg_height - qr_height) / 2

        # Set the QR Code position to the center of the background
        qr_drawing.translate(x_offset, y_offset)

        # Marge the QR Code with the background
        bg_drawing.add(qr_drawing)

        # Convert the drawing to SVG string
        qr_data = renderSVG.drawToString(bg_drawing).replace("\n", "").replace("\t", "")
        qr_svg = ET.fromstring(qr_data)

        # Define the namespace for SVG
        namespaces = {"ns0": "http://www.w3.org/2000/svg"}
        element = qr_svg.find(".//ns0:g[@id='group']", namespaces=namespaces)

    if element is not None:
        # Remove the namespace from the tag
        for elem in element.iter():
            if elem.tag.startswith("{"):
                elem.tag = elem.tag.split("}", 1)[1]

        # Look for the QR code element
        qr_element = element.find(".//g")

        if qr_element is not None:
            qr_element.set("transform", "scale(1,-1) translate(0,-500)")

            # Covert to string
            return ET.tostring(qr_element, encoding="unicode")

    return None


def draw(intensitys: dict, eq_data: dict, eq_id="XXXXXXX-X", bg_path=None, url=None):
    """Draw the Taiwan map with earthquake data.

    Parameters
    ----------
    intensitys : dict
        Required intensity data.
        Format: {
            "county_id": float,
            ...
        }
        where `county_id` is the ID of the county and `float` is the intensity value.

    eq_data : dict
        Required earthquake data.
        Format: {
            "id": str,
            "serial": str,
            "eq": {
                "lat": float,
                "lon": float,
                "mag": float,
                "depth": float,
                "loc": str,
                "time": int,
            },
        }


    eq_id: str
        The ID of the earthquake. Default is "XXXXXXX-X".
        Format: String.

    bg_path : str | path
        `path` can be a file, a file-like, or a file path as str or pathlib.Path.
        Format: File path as str or pathlib.Path.

    url : str
        The text required to generate the QR code.
        Format: String.

    Examples
    --------
    >>> draw(
            eq_data={
                "author": "cwa",
                "id": "1140887",
                "serial": 2,
                "status": 0,
                "final": 0,
                "eq": {
                    "time": 1744126016000,
                    "lon": 123.17,
                    "lat": 24.54,
                    "depth": 15.3,
                    "mag": 5.9,
                    "loc": "宜蘭縣政府東方 144.2 公里 (位於臺灣東部海域)",
                    "max": 3,
                },
                "time": 1744126016000,
            },
            intensitys={
                "TWHUA": 3,
                "TWILA": 2
            },
            bg_path="/path/to/background.svg",
            url="https://www.gj-smart.com/"
        )
    '<svg>...</svg>'

    """
    # Draw SVG from head starting
    svg_parts = [TW_MAP_SVG["head"]]

    # Add Taiwan map SVG parts
    county_id, max_int = _draw_intensitys(svg_parts, intensitys)
    county_name = COUNTY_NAME.get(county_id, county_id)
    max_int = intensity_to_text(round_intensity(max_int))

    # Add epicenter and earthquake information
    _draw_epicenter(svg_parts, eq_data, eq_id, county_name, max_int)

    # Add QR code if URL is provided
    _add_qr_code(svg_parts, url, bg_path)

    # Add legend, copyright, and end tag
    svg_parts.append(TW_MAP_SVG["legend"])
    svg_parts.append(TW_MAP_SVG["copyright"])
    svg_parts.append(TW_MAP_SVG["end"])

    # Join all SVG parts into a single string
    return "\n".join(svg_parts)


def _draw_intensitys(svg_parts: list, intensitys: dict):
    """Draw counties on the map."""
    max_county_id = ""
    max_intensity = 0

    for county_id in COUNTY_CENTERS:
        if county_id in TW_MAP_SVG:
            intensity = intensitys.get(county_id, 0)
            if intensity > max_intensity:
                max_county_id = county_id
                max_intensity = intensity

            intensity_color = INTENSITY_COLORS.get(round_intensity(intensity), DEFAULT_COLOR)
            path_content = TW_MAP_SVG[county_id].replace(f"{{{county_id}_COLOR}}", intensity_color)

            svg_parts.append(path_content)

    return max_county_id, max_intensity


def _draw_epicenter(svg_parts: list, eq_data: dict, eq_id, county_name, max_intensity):
    """Draw the epicenter and earthquake information."""
    eq: dict = eq_data.get("eq", {})

    if eq_id == "XXXXXXX-X":
        eq_id = "震動速報"
        loc_main = "未知區域"
        loc_spec = "震源調查中"
    else:
        epi_latlong = (
            eq.get("lat", TAIWAN_CENTER[0]),
            eq.get("lon", TAIWAN_CENTER[1]),
        )

        offshore_area = is_offshore(epi_latlong)
        if offshore_area:
            svg_parts.append(
                OFFSHORE_ZONES.get(
                    offshore_area,
                    OFFSHORE_ZONES["Sea"],
                )
            )
        else:
            epicenter_x, epicenter_y = latlon_to_svg(epi_latlong)
            _draw_cross(svg_parts, epicenter_x, epicenter_y)

        loc_main, loc_spec = _parse_location(eq.get("loc"), epi_latlong)

    formatted_time = datetime.fromtimestamp(
        round(
            eq.get(
                "time",
                datetime.now(TZ_UTC).timestamp() * 1000,
            )
            / 1000
        ),
        TZ_UTC,
    ).astimezone(TZ_TW)

    svg_parts.append(
        TW_MAP_SVG["info"].format(
            eq_id=eq_id,
            loc_main=loc_main,
            loc_spec=loc_spec,
            time=formatted_time.strftime("%Y/%m/%d %H:%M:%S"),
            max_intensity=" ".join(
                map(
                    str,
                    (
                        county_name,
                        max_intensity,
                    ),
                )
            ),
            mag=eq.get("mag", "---"),
            depth=eq.get("depth", "---"),
            foot_note=_provider_info(
                eq_data.get(
                    "author",
                    eq.get(
                        "author",
                        "ExpTech",
                    ),
                )
            ),
        )
    )


def _provider_info(author: str) -> str:
    """Get the provider information."""
    if author == "cwa":
        return FOOT_NOTE

    return f"Provider: {PROVIDERS.get(author, 'Unknown')}"


def _draw_cross(svg_parts: list, epicenter_x, epicenter_y):
    """Draw a cross at the epicenter."""
    cross1_x = f'x1="{epicenter_x - 10}" x2="{epicenter_x + 10}"'
    cross1_y = f'y1="{epicenter_y - 10}" y2="{epicenter_y + 10}"'
    svg_parts.append(f'<line {cross1_x} {cross1_y} stroke="red" stroke-width="5" />')

    cross2_x = f'x1="{epicenter_x + 10}" x2="{epicenter_x - 10}"'
    cross2_y = f'y1="{epicenter_y - 10}" y2="{epicenter_y + 10}"'
    svg_parts.append(f'<line {cross2_x} {cross2_y} stroke="red" stroke-width="5" />')

    svg_parts.append(f'<circle style="fill:#2e364f;fill-opacity:0.5" cx="{epicenter_x}" cy="{epicenter_y}" r="80" />')


def _parse_location(loc: str | None, epi_latlong: tuple | None = None) -> tuple[str, str]:
    """Parse location into main and specific parts."""
    if loc is None:
        loc_main = "震源調查中"
        loc_spec = "未知區域"
    else:
        loc_parts = loc.split("(")
        loc_main = loc_parts[0].strip() if len(loc_parts) > 0 else loc
        loc_spec = loc_parts[1].strip(")") if len(loc_parts) > 1 else _format_latlong(epi_latlong)

    return loc_main, loc_spec


def _format_latlong(latlong: tuple | None = None):
    if latlong is None:
        return "未知區域"

    lat, lon = latlong

    # lat
    lat_d, lat_m, lat_s = _decimal_to_dms(lat)
    lat_hemisphere = "N" if lat >= 0 else "S"

    # long
    lon_d, lon_m, lon_s = _decimal_to_dms(lon)
    lon_hemisphere = "E" if lon >= 0 else "W"

    lat_str = f"{abs(lat_d):02d}°{abs(lat_m):02d}'{abs(lat_s):04.1f}\"{lat_hemisphere}"
    lon_str = f"{abs(lon_d):03d}°{abs(lon_m):02d}'{abs(lon_s):04.1f}\"{lon_hemisphere}"

    return f"{lat_str} {lon_str}"


def _decimal_to_dms(degree):
    d = int(degree)
    m_float = abs(degree - d) * 60
    m = int(m_float)
    s = (m_float - m) * 60
    return d, m, s


def _add_qr_code(svg_parts: list, url, bg_path):
    """Add QR code to the SVG."""
    if url:
        qrcode_svg = generate_qr_code(url, bg_path, 9)
        svg_parts.append(TW_MAP_SVG["qrcode"].format(qr_code=qrcode_svg))
