# Search／Download Adapter SDK

目前提供離線 Adapter SDK，讓第三方作者在不安裝、不執行程式碼的情況下，先驗證
Search v2 或 Download v2 capability、核心版本範圍、權限、必要工具與
依賴宣告。這不是信任或安裝捷徑；公開套件仍必須走 schema v2 MOD、檔案清單、
Ed25519 簽章與使用者信任流程。

## 建立最小範例

```powershell
.\.venv\Scripts\python.exe -m tools.adapter_sdk create search example.search .\example-search
.\.venv\Scripts\python.exe -m tools.adapter_sdk create download example.download .\example-download
```

範例只建立 `adapter.json` 與空白 `adapter.py`，不建立私鑰、簽章，不自動安裝
Python 套件或外部工具，也不宣稱已支援任何真實網站。

## 離線驗證與相容報告

```powershell
.\.venv\Scripts\python.exe -m tools.adapter_sdk validate .\example-search
.\.venv\Scripts\python.exe -m tools.adapter_sdk validate .\example-search --json
```

驗證器會檢查：

- manifest 欄位、adapter ID、入口路徑、檔案大小與 symlink 邊界；
- Search v2／Download v2 capability 與 provider ID 是否一致；
- 核心最低／最高版本是否包含目前版本；
- 權限是否限於該 adapter 類型允許的最小集合；
- 外部工具與程式依賴是否有界、去重並可產生機器可讀報告。

它不會載入 `adapter.py`、連線到網站、下載依賴或把 adapter 加入 MediaManager。

## 安全與運作界線

- Search adapter 只允許公開網路與可選 JavaScript runtime 宣告。
- Download adapter 可另外宣告下載資料夾、FFmpeg 與 JavaScript runtime；不接受
  Cookie、帳密、任意檔案、shell 或瀏覽器控制權限。
- 外部依賴只做需求提示，不由啟動流程靜默安裝。
- 正式 runtime 仍必須有逾時、取消、程序樹終止、訊息大小與資源上限；失敗時
  回傳單一 MOD 錯誤，不得凍結核心 UI。
- 不得用 adapter 規避 DRM、付費、登入、地區、廣告或網站限制。
