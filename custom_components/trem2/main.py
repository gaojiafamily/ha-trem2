# main.py
from earthquake import get_calculate_intensity
from map import draw

# 地震資料
EARTHQUAKE_DATA = {
    "author": "CWA",
    "id": "114078",
    "serial": 1,
    "status": 0,
    "final": 0,
    "eq": {
        "time": 1743652020000,
        "lon": 120.4,
        "lat": 23.21,
        "depth": 7.3,
        "mag": 4.9,
        "loc": "臺南市政府東北方 32.3 公里 (位於臺南市官田區)",
        "max": 4
    },
    "time": 1743652020000
}

# 計算震度及抵達時間
intensitys = get_calculate_intensity(EARTHQUAKE_DATA["eq"])

# 繪製地圖
with open("output.svg", "w", encoding="utf-8") as f:
    f.write(draw(EARTHQUAKE_DATA, intensitys))
print("SVG 已生成並儲存為 output.svg")