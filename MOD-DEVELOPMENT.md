# 第三方 MOD 開發入口

第三方 MOD 不需要修改 MediaManager 核心。公開可執行 MOD 必須使用 schema v2、
runtime protocol `1.0`、最小 capability、檔案 SHA-256 與發布者 Ed25519 簽章；
安裝成功後仍預設停用。

## 建立範本

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk create example.processor .\example-processor
.\.venv\Scripts\python.exe -m tools.mod_sdk validate .\example-processor\plugin.json
```

網站父／子 MOD：

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk create-site example.site .\example-site `
  --host media.example.com
.\.venv\Scripts\python.exe -m tools.mod_sdk validate-site .\example-site
```

SDK 不產生私鑰、不簽署、不安裝套件，也不執行第三方程式碼。驗證成功只代表
結構與契約可接受，不代表發布者已受信任或 MOD 已獲准啟用。

## 必讀契約

- [完整開發、交付與支援流程](docs/mod-developer-guide.md)
- [MOD 套件格式與生命週期](docs/mod-package-v1.md)
- [網站父／子 MOD 與語言契約](docs/site-mod-group-format.md)
- [Search／Download Adapter SDK](docs/adapter-sdk.md)
- [下載工作契約](docs/downloads-v1.md)

發布者私鑰、Cookie、Token、憑證密碼與 PIN 不得放入套件、Issue、Log 或
Repository。MOD 不得繞過 DRM、登入、付費、地區、廣告或網站限制。
