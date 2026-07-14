# 第三方 MOD 開發與發布流程

MediaManager 的第三方 MOD 採最小權限、獨立程序、明確相容版本與簽章套件。開發者不應直接修改核心程式或把任意 Qt/HTML/JavaScript 注入可信 UI。

## 1. 選擇 MOD 類型

- `processor`、`exporter`、`filter`、`notification`：使用 `python-subprocess` 執行。
- `data-only`：只有資料，不含可執行入口。
- 靜態說明介面：使用簽章清單內的 `ui.json`；只接受 `heading`、`text`、`status` 區塊。
- 網站支援應保持獨立 MOD，並只申請該網站及必要工具權限。

## 2. 建立 manifest v2

套件根目錄必須包含 `plugin.json`、`files.json`、`plugin.sig`。可執行 MOD 的基本 `plugin.json`：

```json
{
  "schema_version": 2,
  "id": "example.publisher.tool",
  "name": "Example Tool",
  "version": "1.0.0",
  "publisher": "example.publisher",
  "plugin_type": "processor",
  "entry_point": "plugin.py",
  "api_version": "1.0",
  "minimum_core_version": "2.0.0",
  "maximum_core_version": "2.9.9",
  "permissions": ["media.read"],
  "external_tools": [],
  "dependencies": [],
  "files_manifest": "files.json",
  "signature": "plugin.sig",
  "runtime": "python-subprocess",
  "runtime_protocol": "1.0",
  "ui_descriptor": "ui.json"
}
```

只宣告實際需要的權限。禁止使用未定義、重複或 unrestricted 類型權限。

## 3. 建立檔案清單

`files.json` 必須列出除三個套件中繼資料檔以外的每個檔案及 SHA-256。路徑必須：

- 使用相對 POSIX 路徑。
- 大小寫不重複。
- 不含 `..`、絕對路徑、Windows 保留名稱、ADS 或 symbolic link。
- 不夾帶 EXE/MSI 安裝器。

## 4. 簽章

使用發行者自己的 Ed25519 私鑰，對下列精確位元組簽章；JSON 簽章後不可重新格式化：

```text
"MediaManager-MOD-v1\0"
+ uint64_be(len(plugin.json)) + raw_plugin_json_bytes
+ uint64_be(len(files.json))  + raw_files_json_bytes
```

`plugin.sig` 可使用原始 64-byte 簽章或 Base64。公開金鑰是 Base64 編碼的原始 32-byte Ed25519 金鑰，可加 `ed25519:` 前綴。私鑰不得放入 MOD、GitHub 倉庫或使用者安裝包。

## 5. 封裝與測試

1. 將套件內容壓成 ZIP，副檔名改為 `.modpkg`。
2. 使用乾淨的 Portable 測試資料夾。
3. 先在「MOD 管理」新增發行者公開金鑰並核對 fingerprint。
4. 安裝 `.modpkg`；新安裝與更新後一律維持停用。
5. 檢查請求權限、缺少相依工具、核心版本上下限及錯誤回復。
6. 只有 `NORMAL` 模式可啟用可執行 MOD；`SAFE_MODE` 可驗證及安裝，但保持停用。
7. 測試更新、回滾、移除、永久清理及中斷後重新啟動。

## 6. UI 規則

`ui.json` schema v1 只允許：

- `schema_version`
- `page_id`
- `title`
- 最多 40 個靜態 `heading`、`text` 或 `status` blocks

不接受 HTML、URL、script、Qt object 或 callback。互動操作應透過已版本化的核心合約與明確權限實作，不應藏在 UI 描述檔。

## 7. 更新規則

- 保持相同 plugin ID 與 publisher。
- 使用更高的 SemVer 版本。
- 重新產生完整 SHA-256 清單與簽章。
- 使用者必須重新確認更新後的權限集合。
- 更新失敗時必須能回到上一個已驗證版本；不要依賴線上安裝腳本修改核心。

## 8. 提交建議

目前尚未提供自動 MOD 市集。可先透過 [建議表單](https://forms.gle/iUMyEDojsASoFyY16) 提交：

- MOD 名稱、版本、用途與原始碼/文件網址
- 發行者 ID、公鑰 fingerprint
- 權限與外部工具清單
- 支援的 MediaManager 核心版本
- 測試結果、授權條款與已知限制

正式納入前仍需安全審查；不接受廣告、遙測、強制帳號、DRM/付費/地區/驗證繞過或靜默下載其他執行檔。

