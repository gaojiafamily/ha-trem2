## 解決字體及依賴安裝問題

> [!IMPORTANT]
> 請務必詳讀，並謹慎操作，在開始前建議先備份。

---

### SSH 附加元件 (推薦)
1. 前往附加元件商店<br>
[![在您的 Home Assistant 實例中打開此附加元件。](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_ssh&repository_url=https%3A%2F%2Fgithub.com%2Fhassio-addons%2Frepository)
2. 安裝其中一個 SSH 附加元件（需在使用者設定檔啟用進階模式，詳細說明請參閱 [此處](https://github.com/hassio-addons/addon-ssh/blob/main/ssh/DOCS.md#installation)）
3. 根據 [文檔](https://github.com/hassio-addons/addon-ssh/blob/main/ssh/DOCS.md#configuration) 配置您選擇的 SSH 附加元件
4. 確保禁用保護模式並啟動 SSH 附加元件
5. 連接到 SSH 附加元件
6. 在終端輸入以下指令進入 Home Assistant CLI：
```bash
login
docker exec -it homeassistant bash
```
![image](https://github.com/J1A-T13N/ha-trem/assets/29163857/36748f45-03c1-4f3e-814e-cd54167606b7)
7. 在終端中執行以下指令以安裝字體及依賴
```bash
apk add cairo
mkdir -p ~/.fonts
cp custom_components/trem2/assets/NotoSansTC-Regular.ttf ~/.fonts
fc-cache -fv
fc-list
```

![image](https://github.com/J1A-T13N/ha-trem/assets/29163857/b207f304-65bd-4ed2-aefb-60caf51f412c)
8. 如果一切成功，[繼續設定流程](../README.md#config)

> [!NOTE]
> 安狀依賴及字型緩存更新可能需要一些時間，請耐心等待。
<hr>
<br>

### Docker Terminal
1. 打開終端機並登入
2. 使用以下指令進入容器
```bash
docker exec -it homeassistant bash
```
3. 在終端中複製並貼上以下指令以安裝所需依賴
```bash
apk add cairo
mkdir -p ~/.fonts
cp custom_components/trem2/assets/NotoSansTC-Regular.ttf ~/.fonts
fc-cache -fv
fc-list
```

4. 如果一切成功，[繼續設定流程](../README.md#config)

> [!NOTE]
> 安狀依賴及字型緩存更新可能需要一些時間，請耐心等待。
<hr>
<br>

### 字型來源及授權
- **Noto Sans CJK**：由 Google 開發的開源字型，支援中日韓文字。
- 授權：Apache License 2.0
