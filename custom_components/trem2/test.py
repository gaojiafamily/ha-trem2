"""CWA QR Code Generator with SVG Background."""

import io

from defusedxml import ElementTree as ET
from reportlab.graphics import renderSVG
import segno
from svglib.svglib import svg2rlg

# 生成 QR Code
qrcode = segno.make(
    "https://www.cwa.gov.tw/V8/C/E/EQ/EQ114078-0403-114700.html",
    error="h",
)

# 將 QR Code 保存到 BytesIO 作為 SVG
qr_svg = io.BytesIO()
qrcode.save(qr_svg, scale=10, kind="svg")
qr_svg.seek(0)  # 重置指針到開頭

# 讀取背景 SVG 文件
bg_svg = "assets/CWA_Logo.svg"

# 使用 svglib 載入背景和 QR Code
bg_drawing = svg2rlg(bg_svg)  # 載入背景 SVG
qr_drawing = svg2rlg(qr_svg)  # 載入 QR Code SVG

# 獲取背景 SVG 的尺寸
bg_width = bg_drawing.width
bg_height = bg_drawing.height

# 獲取 QR Code 的尺寸
qr_width = qr_drawing.width
qr_height = qr_drawing.height

# 計算居中的 x, y 座標
x_offset = (bg_width - qr_width) / 2
y_offset = (bg_height - qr_height) / 2

# 移動 QR Code 到居中位置
qr_drawing.translate(x_offset, y_offset)

# 將 QR Code 添加到背景上
bg_drawing.add(qr_drawing)

# 保存最終結果為 SVG
qr_data = renderSVG.drawToString(bg_drawing).replace("\n", "").replace("\t", "")
qr_svg = ET.fromstring(qr_data)

# 定義命名空間映射
namespaces = {"ns0": "http://www.w3.org/2000/svg"}
element = qr_svg.find(".//ns0:g[@id='group']", namespaces=namespaces)

if element is not None:
    # 移除命名空間前綴
    for elem in element.iter():
        if elem.tag.startswith("{"):
            elem.tag = elem.tag.split("}", 1)[1]

    # 找到 group 元素下的子節點
    qr_element = element.find(".//g")

    if qr_element is not None:
        qr_element.set("transform", "scale(1,-1) translate(0,-500)")

        # 轉換為字串
        qrcode = ET.tostring(qr_element, encoding="unicode")
        print(qrcode)  # noqa: T201
    else:
        print("找不到 QR Code 元素")  # noqa: T201
else:
    print("建立 QR Code 失敗")  # noqa: T201
