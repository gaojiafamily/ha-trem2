<h1 align="center">Taiwan Real-time Earthquake Monitoring for HA</h1>

[![GitHub Release][releases-shield]][releases]
[![hacs_custom][hacs_custom_shield]][hacs_custom]
[![License][license-shield]](LICENSE)

[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Contributors][contributors-shield]][contributors-url]

[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

<hr>

English | [繁體中文](README_zhHant.md)<br>


## Preview
![trem2](https://raw.githubusercontent.com/jayx1011/jayx1011/refs/heads/main/repositories/ha-trem2/preview.png)
<br>
1. The property of Image can be used to obtain the estimated seismic intensity.
2. [Event triggers](README.md#Event) are now supported.
3. **Selectable and browsable list of the latest 5 earthquake reports.**

![trem2](https://raw.githubusercontent.com/jayx1011/jayx1011/refs/heads/main/repositories/ha-trem2/trem2.png)
<br>
**The recent report data is displayed by default**


> [!IMPORTANT]
> The source of earthquake early warning is provided by ExpTech Studio and is for reference only.<br>
> The actual results are subject to the content published by [CWA](https://scweb.cwa.gov.tw/en-US).<br>
> Some features require a subscription to the Enhanced Computing Service ("ECS").

<hr>
<br>


## Feature

- [x] Isoseismal map image.
- [x] Simulator earthquake service.
- [ ] Calculate arrival forecast based on your location (ECS only).
- [x] Intensity Notification (Exptech VIP only).
- [ ] Tsunami Notification (Exptech VIP only).

<hr>
<br>

## Legal

- [Terms of Service](legal/TERMS_zhHant.md)
- [Privacy Policy](legal/PRIVACY_zhHant.md)

<hr>
<br>

## Getting Started
### For Your Protection
Before using, please read and comply with the [Terms of Service](legal/TERMS_zhHant.md) and [Privacy Policy](legal/PRIVACY_zhHant.md).

### Installation
#### Using [HACS](https://hacs.xyz/) (recommended)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gaojiafamily&repository=ha-trem2&category=Integration)

#### Manual
1. Create `config/custom_components` folder if not existing.
2. Copy `trem2` into `custom_components` folder.

### Config
**Please use the config flow of Home Assistant.**

With GUI. Configuration > Integration > Add Integration > Taiwan Real-time Earthquake Monitoring 2
   - If the integration didn't show up in the list please REFRESH the page
   - If the integration is still not in the list, you need to clear the browser cache.

<hr>
<br>


### Reference
## Event
| Name | Summary | Note |
| :------------ | :------------ | :------------ |
| trem2_notification | Earthquake Early Warning | Including simulation <br> the origin field will display LOCAL for simulations <br> and REMOTE when receiving a real server alert |
| trem2_report | Earthquake Report | |
| trem2_image_saved | Image Saved | |
## Service
| Name | Summary | Note |
| :------------ | :------------ | :------------ |
| Save Image | Saved Image, with the file name as the eew or report id. | The image use relative paths and are stored in the 'www' directory by default. |
| Simulating Earthquake | Please refer to the example data. | To stop simulation, `leave empty` or un-check. |
| Set Http Node | Switch the `HTTP` server node or specify the server location. | If the operation fails, it will automatically fallback or retry available servers with exponential backoff. |
| Set WebSocket Node | Switch the `WebSocket` server node or specify the server location. | **ExpTech VIP Only** |

<hr>
<br>

## Data Source
- [x] Http protocol
- [x] Websocket protocol (Exptech VIP only)
- [x] Custom server (Using [Service](README.md#Service))


<hr>
<br>

## Known issues

<br>

*An API server can be monitored [here](https://status.exptech.dev).*

<hr>
<br>


### Subscribe Plan
~~Based on the donate amount, every $15 grants six months of ECS access.~~

> [!NOTE]
> When using ECS or ExpTech VIP services, please review the [Terms of Service](legal/TERMS_zhHant.md#7-訂閱條款) and [Privacy Policy](legal/PRIVACY_zhHant.md).<br>
> ECS access will be released soon.

<p>You can goto https://exptech.com.tw/pricing to subscribe Exptech VIP.</p>
<br>

<hr>
<br>


## Donate

| Buy me a coffee | LINE Bank | JAKo Pay |
| :------------: | :------------: | :------------: |
| <img src="https://github.com/user-attachments/assets/48a3bae6-f342-4d74-ba95-8db82cb44430" alt="Buy me a coffee" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/ee77e2b6-3409-43da-b2b8-14878c5660bb" alt="Line Bank" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/cfaeab8f-576c-43e7-be52-8581bf263cd9" alt="JAKo Pay" height="200" width="200">  |

> [!NOTE]
> Your sponsorship will be used to maintain the open-source project and develop the ECS service.<br>
> All related rights and obligations are governed by the [Terms of Service](legal/TERMS_zhHant.md).
<hr>
<br>


## Contribution

- ExpTech Studio `Data Source`

<p>I would like to thank everyone who has helped me and every partner in the community for their generous help.</p>

<hr>
<br>


## License & Terms
- **Open Source License**: This project is licensed under the [AGPL-3.0 License](https://www.gnu.org/licenses/agpl-3.0.html), allowing free use, modification, and distribution. For details, see the [Terms of Service](legal/TERMS_zhHant.md#6-授權條款).
- **Enhanced Computing Service (ECS)**: Subscription is required and you must comply with the [Terms of Service](legal/TERMS_zhHant.md#7-訂閱條款), including refund policies and usage restrictions.
- **Font License**: This project uses the [Noto Sans TC font](https://fonts.google.com/specimen/Noto+Sans+TC)、[Noto Sans SC font](https://fonts.google.com/specimen/Noto+Sans+SC)、[Noto Sans JP font](https://fonts.google.com/specimen/Noto+Sans+JP). For more information, see the [Terms of Service](legal/TERMS_zhHant.md#6-授權條款).

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
