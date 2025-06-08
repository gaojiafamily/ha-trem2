"""Helper constants."""

from __future__ import annotations

from enum import Enum


class WebSocketService(Enum):
    """Represent the supported WebSocket service."""

    REALTIME_STATION = "trem.rts"  # 即時地動資料
    REALTIME_WAVE = "trem.rtw"  # 即時地動波形圖資料
    EEW = "websocket.eew"  # 地震速報資料
    TREM_EEW = "trem.eew"  # TREM 地震速報資料
    REPORT = "websocket.report"  # 中央氣象署地震報告資料
    TSUNAMI = "websocket.tsunami"  # 中央氣象署海嘯資訊資料
    CWA_INTENSITY = "cwa.intensity"  # 中央氣象署震度速報資料
    TREM_INTENSITY = "trem.intensity"  # TREM 震度速報資料
