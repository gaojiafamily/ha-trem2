<h1 align="center">Taiwan Real-time Earthquake Monitoring for HA</h1>

![Logo](https://raw.githubusercontent.com/gaojiafamily/ha-trem2/master/docs/media/logo.png)

[![GitHub Release][releases-shield]][releases]
[![hacs_custom][hacs_custom_shield]][hacs_custom]
[![License][license-shield]](LICENSE)

[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Contributors][contributors-shield]][contributors-url]

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

<hr>

[English](README.md) | 繁體中文<br>


## 預覽



<hr>
<br>


> [!IMPORTANT]
>地震預警來源由 ExpTech Studio 提供，僅供參考<br>
>實際結果以 [中央氣象署](https://scweb.cwa.gov.tw/en-US) 公佈的內容為準<br>
>部分功能需要訂閱增強運算服務 (Enhanced Computing Service，下稱 ECS)

<hr>
<br>


## 功能

- [x] 等震線圖影像 (可儲存為檔案)
- [ ] 模擬地震服務
- [ ] 根據您的位置預測抵達時間 (僅限 ECS)
- [ ] RTS 通知 (僅限 Exptech VIP)
- [ ] 海嘯通知 (僅限 Exptech VIP)

<hr>
<br>


## 安裝

### 推薦使用 [HACS](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gaojiafamily&repository=ha-trem&category=Integration)

### 手動
1. 如果不存在，請建立 `config/custom_components` 資料夾
2. 將 `trem2` 複製到 `custom_components` 資料夾中

<hr>
<br>


## 設定

**請使用 Home Assistant 的設定流程**

使用圖形介面：設定 > 整合 > 新增整合 > 台灣即時地震監測 2
   - 如果整合未出現在列表中，請重新整理頁面
   - 如果整合仍未出現在列表中，您可能需要清除快取

<hr>
<br>


## 資料來源
- [x] Http 協定
- [ ] Websocket 協第 (Exptech VIP only)
- [ ] 自訂伺服器 (ECS only)


## 已知問題

<hr>
<br>

*API伺服器狀態可於[此處](https://status.exptech.dev)查看*


### ECS/Exptech VIP
<p>根據您的贊助金額，每 $15 可以獲得半年 ECS 授權.</p>
<p>您可以到 [https://exptech.com.tw/pricing](https://exptech.com.tw/pricing) 訂閱 Exptech VIP</p>
<br>

<hr>
<br>


## 贊助

| Buy me a coffee | LINE Bank | JAKo Pay |
| :------------: | :------------: | :------------: |
| <img src="https://github.com/user-attachments/assets/48a3bae6-f342-4d74-ba95-8db82cb44430" alt="Buy me a coffee" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/ee77e2b6-3409-43da-b2b8-14878c5660bb" alt="Line Bank" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/cfaeab8f-576c-43e7-be52-8581bf263cd9" alt="JAKo Pay" height="200" width="200">  |

<hr>
<br>


## 貢獻

- ExpTech Studio `資料來源`

<p>感謝所有幫助過我的人，以及社群中的每一位合作夥伴，熱心且無私的幫助</p>

<hr>
<br>


## License
這是一個開源客戶端工具，採用 AGPL-3.0 許可證，允許任何人自由使用、修改和分發
此工具需要訂閱才能使用我們的增強運算服務
**2024-08-15 與 ExpTech Studio 達成協議**


[releases-shield]: https://img.shields.io/github/release/gaojiafamily/ha-trem2.svg?style=for-the-badge
[releases]: https://github.com/gaojiafamily/ha-trem2/releases
[hacs_custom_shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs_custom]: https://hacs.xyz/docs/faq/custom_repositories
[stars-shield]: https://img.shields.io/github/stars/gaojiafamily/ha-trem2.svg?style=for-the-badge
[stars-url]: https://github.com/gaojiafamily/ha-trem2/stargazers
[issues-shield]: https://img.shields.io/github/issues/gaojiafamily/ha-trem2.svg?style=for-the-badge
[issues-url]: https://github.com/gaojiafamily/ha-trem2/issues
[contributors-shield]: https://img.shields.io/github/contributors/gaojiafamily/ha-trem2.svg?style=for-the-badge
[contributors-url]: https://github.com/gaojiafamily/ha-trem2/graphs/contributors
[license-shield]: https://img.shields.io/github/license/gaojiafamily/ha-trem2.svg?style=for-the-badge
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/j1at13n
