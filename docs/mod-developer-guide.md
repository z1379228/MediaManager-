# MediaManager 第三方 MOD 開發流程

第三方 MOD 不需要修改核心原始碼。開發者先建立 schema v2 專案，僅申請必要
權限，完成檔案清單與 Ed25519 簽署後，再交由使用者安裝。未簽署、發布者未受
信任或權限超出 manifest 的可執行 MOD 不會啟動。

## 建立範本

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk create example.processor .\example-processor
```

範本刻意不產生私鑰、簽章或偽造 `files.json`。發布者應在自己的離線發行環境
建立檔案 SHA-256 清單與 `plugin.sig`，私鑰不得放入專案或 `.modpkg`。

## 安裝前檢查

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk validate .\example-processor\plugin.json
.\.venv\Scripts\python.exe -m tools.mod_sdk validate .\example.processor.modpkg
```

第一個命令檢查 manifest、核心版本、API 與執行協定。第二個命令額外檢查 ZIP
結構、路徑、宣告檔案及 SHA-256，但不把結構正確誤當成發布者可信；簽章與
Trust Store 仍在正式安裝時驗證。

## 生命週期

1. 使用者匯入發布者公鑰並明確信任發布者。
2. 安裝器驗證套件後以停用狀態安裝。
3. 使用者審查權限並啟用；核心只發出簽署 manifest 允許的短效權限。
4. 更新必須保持相同 ID 與發布者，舊版留在備份區供回復。
5. 移除先進入隔離區；永久清除是另一個不可逆確認步驟。

目前公開契約為 API `1.0`、runtime protocol `1.0`。UI 僅接受簽署的宣告式
`ui.json`；不可注入 HTML、Qt 物件、任意腳本或廣告。

網站功能若要整合到可信 UI，必須維持「一個網域家族一個父 MOD、額外能力拆成子
MOD」的結構，並提供 `en`、`ja`、`zh-CN`、`zh-TW` 四份完整語言資源。父 MOD
停用時子 MOD 不顯示且不可執行；網站權限、網址允許清單與 provider 不得跨群組共用。
詳細契約請見 [`site-mod-group-format.md`](site-mod-group-format.md)。

需要開發網站搜尋或下載適配器時，先依
[`adapter-sdk.md`](adapter-sdk.md) 建立 Search／Download v2 離線範例與相容
報告，再封裝進正式簽署 MOD；Adapter SDK 驗證成功不等於已受信任或可啟用。
