## Solve Font and Dependency Installation Issues

> [!IMPORTANT]
> Please read carefully and proceed with caution. It is recommended to back up your system before starting.

---

### SSH Add-on (Recommended)
1. Go to the Add-on store<br>
[![Open this add-on in your Home Assistant instance.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_ssh&repository_url=https%3A%2F%2Fgithub.com%2Fhassio-addons%2Frepository)
2. Configure the SSH add-on you chose by following its [documentation](https://github.com/hassio-addons/addon-ssh/blob/main/ssh/DOCS.md#installation).
3. Ensure that protection mode is disabled and start the SSH add-on.
4. Connect to the SSH add-on.
5. Enter the following commands in the terminal to access the Home Assistant CLI:
```bash
login
docker exec -it homeassistant bash
```
![image](https://github.com/J1A-T13N/ha-trem/assets/29163857/36748f45-03c1-4f3e-814e-cd54167606b7)
6. Paste the following commands into the terminal to install fonts and dependencies:
```bash
apk add cairo
mkdir -p ~/.fonts
cp custom_components/trem2/assets/NotoSansTC-Regular.ttf ~/.fonts
fc-cache -fv
fc-list
```

![image](https://github.com/J1A-T13N/ha-trem/assets/29163857/b207f304-65bd-4ed2-aefb-60caf51f412c)
8. everything is successful, proceed with the [configuration process](../README.md#config)

> [!NOTE]
> Installing dependencies and updating the font cache may take some time. Please be patient.
<hr>
<br>

### Docker Terminal
1. Open a terminal and log in.
2. Use the following command to enter the container:
```bash
docker exec -it homeassistant bash
```
3. Copy and paste the following commands into the terminal to install the required dependencies:
```bash
apk add cairo
mkdir -p ~/.fonts
cp custom_components/trem2/assets/NotoSansTC-Regular.ttf ~/.fonts
fc-cache -fv
fc-list
```

4. everything is successful, proceed with the [configuration process](../README.md#config)

> [!NOTE]
> Installing dependencies and updating the font cache may take some time. Please be patient.
<hr>
<br>

### Font Source and Licensing
- **Noto Sans CJK**: An open-source font developed by Google that supports Chinese, Japanese, and Korean characters.
- License: Apache License 2.0
