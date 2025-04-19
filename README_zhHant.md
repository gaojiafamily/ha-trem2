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


## 介紹
![image](https://github.com/user-attachments/assets/96193e8b-d820-40f6-acb1-3e8f1c481e3b)
1. 預估震度可以到圖片屬性查看.
2. 自動化可以[使用事件](README_zhHant.md#事件)來達成.

![trem2](https://github.com/user-attachments/assets/3d6af2ca-139e-41dd-9a93-03d9c340f7ad)
**預設顯示上一筆地震報表資料**


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

## 法律文件

- [服務條款](legal/TERMS_zhHant.md)
- [隱私權政策](legal/PRIVACY_zhHant.md)

<hr>
<br>

## 開始使用
### 為了您的權益
**使用前，請閱讀並遵守[服務條款](legal/TERMS_zhHant.md#7-訂閱條款)與[隱私政策](legal/PRIVACY_zhHant.md)**

### 安裝
#### 推薦使用 [HACS](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gaojiafamily&repository=ha-trem2&category=Integration)

#### 手動
1. 如果不存在，請建立 `config/custom_components` 資料夾
2. 將 `trem2` 複製到 `custom_components` 資料夾中

### 設定
**請使用 Home Assistant 的設定流程**

使用圖形介面：設定 > 整合 > 新增整合 > Taiwan Real-time Earthquake Monitoring 2
   - 如果整合未出現在列表中，請重新整理頁面
   - 如果整合仍未出現在列表中，您可能需要清除快取

<hr>
<br>


## 事件
| 名稱 | 說明 | 備註 |
| :------------ | :------------ | :------------ |
| trem2_notification | 地震速報 | 包含模擬(origin 會顯示 LOCAL) <br> 來自伺服器的則會顯示 REMOTE |
| trem2_report | 地震報告已更新時會觸發 | |
| trem2_image_saved | 圖片儲存時會觸發 | |


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


### 訂閱服務
~~根據您的贊助金額，每 $15 可以獲得半年 ECS 授權.~~

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

> [!NOTE]
> 您的贊助將用於維護開源專案與 ECS 服務開發，相關權利義務依[服務條款](legal/TERMS_zhHant.md)規範。
<hr>
<br>


## 貢獻

- ExpTech Studio `資料來源`

<p>感謝所有幫助過我的人，以及社群中的每一位合作夥伴，熱心且無私的幫助</p>

<hr>
<br>


## 授權與條款
- **開源授權**：本專案採用 [AGPL-3.0 授權](https://www.gnu.org/licenses/agpl-3.0.html)，允許自由使用、修改與散布，詳見[服務條款](legal/TERMS_zhHant.md#6-授權條款)。
- **增強運算服務 (ECS)**：需訂閱並遵守[服務條款](legal/TERMS_zhHant.md#7-訂閱條款)，包含退款政策與使用限制。
- **字體授權**：本專案使用 [Noto Sans TC 字體](https://fonts.google.com/specimen/Noto+Sans+TC)，更多資訊詳見[服務條款](legal/TERMS_zhHant.md#6-授權條款)。

<hr>
<br>


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
