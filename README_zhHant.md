<h1 align="center">Taiwan Real-time Earthquake Monitoring for HA</h1>

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
![trem2_preview](https://github.com/user-attachments/assets/a1081fd4-baef-476c-bc48-ef823774edc4)

> [!IMPORTANT]
> 地震預警來源由 ExpTech Studio 提供，僅供參考<br>
> 實際結果以 [中央氣象署](https://scweb.cwa.gov.tw/en-US) 公佈的內容為準<br>
> 部分功能需要訂閱增強運算服務 (Enhanced Computing Service，下稱 ECS)

<hr>
<br>


## 功能

- [x] 等震線圖影像
- [x] 模擬地震服務
- [ ] 根據您的位置預測抵達時間 (僅限 ECS)
- [ ] RTS 通知 (僅限 Exptech VIP)
- [ ] 海嘯通知 (僅限 Exptech VIP)

<hr>
<br>

## 安裝

### 推薦使用 [HACS](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gaojiafamily&repository=ha-trem2&category=Integration)

### 手動
1. 如果不存在，請建立 `config/custom_components` 資料夾
2. 將 `trem2` 複製到 `custom_components` 資料夾中

<hr>
<br>


## 設定

**請使用 Home Assistant 的設定流程**

使用圖形介面：設定 > 整合 > 新增整合 > Taiwan Real-time Earthquake Monitoring 2
   - 如果整合未出現在列表中，請重新整理頁面
   - 如果整合仍未出現在列表中，您可能需要清除快取

<hr>
<br>


## 資料來源
- [x] Http 協定
- [ ] Websocket 協定 (Exptech VIP only)
- [ ] 自訂伺服器 (ECS only)


<hr>
<br>

## 已知問題
- [x] QR Code 不正確

<br>

*伺服器狀態可以在這[查看](https://status.exptech.dev)*

<hr>
<br>


### ECS/Exptech VIP
<p>-根據您的贊助金額，每 $15 可以獲得半年 ECS 授權.-</p>

> [!NOTE]
> ECS 功能將於近期推出

<p>您可以到 https://exptech.com.tw/pricing 訂閱 Exptech VIP</p>
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


## 授權
1. 這是一個開源客戶端工具，採用 AGPL-3.0 許可證，允許任何人自由使用、修改和分發
2. 此工具需要訂閱才能使用我們的增強運算服務

> **2024-08-15 與 ExpTech Studio 達成協議**

<hr>
<br>


## 字體授權摘要
- **署名要求**:
  - Noto Sans TC 字體由 Google 及其他貢獻者開發。更多資訊請參閱 [Google Fonts](https://fonts.google.com/specimen/Noto+Sans+TC)
- **使用方式**:
  - 字體文件（NotoSansTC-Regular.ttf）將複製至使用者的字體目錄
- **授權許可範圍**:
  - 商業用途
  - 修改
  - 分發
  - 個人使用
- **限制條款**:
  - 無擔保
  - 責任限制
- **強制條件**:
  - 必須包含授權條款及版權聲明於授權內容中
  - 修改後的衍生作品必須以相同授權條款釋出

> [!INFO]
> 本存儲庫包含的 Noto Sans TC 字體僅限用於本項目內
> 若需於本存儲庫外發佈此字體，必須遵守 SIL 開放字體授權條款 規定
> 完整條款詳見 [SIL Open Font License](https://scripts.sil.org/OFL)


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
