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


## Screenshots
![trem2_preview](https://github.com/user-attachments/assets/a1081fd4-baef-476c-bc48-ef823774edc4)

> [!IMPORTANT]
> The source of earthquake early warning is provided by ExpTech Studio and is for reference only.<br>
> The actual results are subject to the content published by [CWA](https://scweb.cwa.gov.tw/en-US).<br>
> Some features require a subscription to the Enhanced Computing Service ("ECS").

<hr>
<br>


## Feature

- [x] Isoseismal map image.
- [ ] Simulator earthquake service.
- [ ] Calculate arrival forecast based on your location (ECS only).
- [ ] RTS Notification (Exptech VIP only).
- [ ] Tsunami Notification (Exptech VIP only).

<hr>
<br>


## Prerequisite

> [!IMPORTANT]
> Before installing this integration, please ensure your environment meets the necessary requirements for dependencies and fonts.
> Detailed instructions are provided in the [Prerequisite Documentation](Prerequisite.md).

> [!NOTE]
> We are actively working on a proposal to pre-install these dependencies in the Home Assistant Core.
> This will reduce manual setup requirements. See [Community Proposal](#community-proposal-pre-install-dependencies-in-home-assistant-core) for details.

<hr>
<br>

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gaojiafamily&repository=ha-trem2&category=Integration)

### Manual
1. Create `config/custom_components` folder if not existing.
2. Copy `trem2` into `custom_components` folder.

<hr>
<br>


## Config

**Please use the config flow of Home Assistant.**

With GUI. Configuration > Integration > Add Integration > Taiwan Real-time Earthquake Monitoring 2
   - If the integration didn't show up in the list please REFRESH the page
   - If the integration is still not in the list, you need to clear the browser cache.

<hr>
<br>


## Data Source
- [x] Http protocol
- [ ] Websocket protocol (Exptech VIP only)
- [ ] Custom server (ECS only)


<hr>
<br>

## Known issues
- [ ] Todo: [Pre-install Dependencies in Home Assistant Core](#community-proposal-pre-install-dependencies-in-home-assistant-core)

<br>

*An API server can be monitored [here](https://status.exptech.dev).*

<hr>
<br>


## Community Proposal: Pre-install Dependencies in Home Assistant Core

To simplify the installation process for users and developers, we propose adding the following dependencies to the default Home Assistant Core:

### System-level Dependencies:
- **cairo**: Required for font rendering and SVG processing.

### Benefits:
1. Reduces manual setup steps, especially for non-technical users.
2. Ensures compatibility with integrations and custom components that rely on these dependencies.
3. Enhances developer productivity by providing a ready-to-use environment.

### Next Steps:
We plan to submit this proposal to the Home Assistant GitHub repository as a Feature Request. This will include testing results and detailed reasoning to support the inclusion of these dependencies in the official Docker image.

<hr>
<br>


### ECS/Exptech VIP
<p>Based on the donate amount, every $15 grants six months of ECS access.</p>

> [!NOTE]
> ECS access will be released soon.

<p>You can goto https://exptech.com.tw/pricing to subscribe Exptech VIP.</p>
<br>

<hr>
<br>


## Donate

| Buy me a coffee | LINE Bank | JAKo Pay |
| :------------: | :------------: | :------------: |
| <img src="https://github.com/user-attachments/assets/48a3bae6-f342-4d74-ba95-8db82cb44430" alt="Buy me a coffee" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/ee77e2b6-3409-43da-b2b8-14878c5660bb" alt="Line Bank" height="200" width="200">  | <img src="https://github.com/user-attachments/assets/cfaeab8f-576c-43e7-be52-8581bf263cd9" alt="JAKo Pay" height="200" width="200">  |

<hr>
<br>


## Contribution

- ExpTech Studio `Data Source`

<p>I would like to thank everyone who has helped me and every partner in the community for their generous help.</p>

<hr>
<br>


## License
This is an open-source client tool licensed under the AGPL-3.0 license, allowing anyone to freely use, modify, and distribute it.<br>
This tool requires a subscription to use our enhanced computing service.<br>
**2024-08-15 Agreement reached with ExpTech Studio.**


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
