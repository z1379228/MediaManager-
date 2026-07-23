# MediaManager 第三方 MOD 開發流程

第三方 MOD 不需要修改核心原始碼。開發者先建立 schema v2 專案，僅申請必要
權限，完成檔案清單與 Ed25519 簽署後，再交由使用者安裝。未簽署、發布者未受
信任或權限超出 manifest 的可執行 MOD 不會啟動。

## 建立範本

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk create example.processor .\example-processor
```

一般範本會依目前開發版自動填入核心相容版本，並產生只含靜態文字區塊的
`ui.json`；`en`、`ja`、`zh-CN`、`zh-TW` 四種核心語言已預先建立。

網站 MOD 請改用父／子範本：

```powershell
.\.venv\Scripts\python.exe -m tools.mod_sdk create-site example.site .\example-site --host media.example.com
.\.venv\Scripts\python.exe -m tools.mod_sdk validate-site .\example-site
```

這會建立 data-only 父 MOD 與依賴父層的 `example.site.download` 子 MOD；網站搜尋、
彈幕或其他功能可仿照 download 子目錄另建子套件，但每個子 MOD 都必須在
`dependencies` 指向同一父 MOD。每個 `--host` 必須是該網站家族實際負責的標準 DNS
名稱，不接受 URL、萬用字元、IP 或跨網站共用。`validate-site` 會離線檢查父／子 ID、
相依關係、host ownership、最小網路／媒體權限、schema v2、runtime protocol 1.0、
30 秒請求逾時、3 秒取消寬限、程序樹終止政策與四語宣告式 UI，不安裝也不執行 MOD
程式碼。

範本刻意不產生私鑰、簽章或偽造 `files.json`。發布者應在自己的離線發行環境
建立檔案 SHA-256 清單與 `plugin.sig`，私鑰不得放入專案或 `.modpkg`。

## 交付、安裝與支援責任

第三方 MOD 支援以可驗證交付物分工，不讓第三方程式碼直接取得核心或可信 UI
控制權：

| 角色 | 負責 | 不負責 |
|---|---|---|
| 第三方作者 | MOD 原始碼、manifest、最小權限、測試、版本相容、Ed25519 簽署、變更紀錄與使用者支援 | MediaManager release 私鑰、核心 Trust Store 決策、替使用者自動啟用 |
| 使用者 | 從獨立管道核對 publisher 公鑰／指紋、審查權限、安裝、啟用、更新、回復與移除決定 | 向作者或 MediaManager 提供私鑰、Cookie、Token、憑證密碼或 PIN |
| MediaManager 核心 | 格式／簽章／hash／相容性驗證、最小 capability、dependency graph、受控 host、journal recovery、隔離移除與宣告式 UI | 為第三方網站適配正確性背書、代管作者私鑰、繞過網站或安全限制 |

建議交付包包含：

- 唯一 `.modpkg`、對應 SHA-256、MOD ID／SemVer、publisher ID 與公開金鑰指紋。
- 支援的 MediaManager core 範圍、API `1.0`／runtime protocol `1.0`、要求權限與
  transitive dependency 清單。
- 版本變更、已知限制、回復版本、問題回報位置與維護狀態。
- 網站 MOD 另列 exact host ownership；不接受 wildcard、IP、登入資料或跨網站共用權限。

使用者端依序執行：

`核對 publisher → 匯入並信任公鑰 → 驗證／安裝 .modpkg（預設停用） → 審查權限與 dependency → 明確啟用 → 自我檢查`

任何一步失敗都停止，不自動降低驗證。問題分流如下：

- SDK／manifest／package 驗證失敗：作者先用下方離線命令重現並修正。
- publisher 不受信任或指紋不符：停止安裝，改由獨立管道向作者核對；不可只依套件內資料信任。
- capability／dependency／core range 不符：由作者縮小權限、補齊依賴或發布相容版本。
- 安裝交易、journal recovery、quarantine 或 host 啟動失敗：回報 MediaManager 核心，
  附去識別的 MOD ID／版本／publisher 指紋、核心版本、錯誤分類與最小重現步驟。
- MOD 自身功能、網站解析或輸出內容錯誤：由第三方作者處理；核心不以放寬簽章、
  host allowlist、登入、DRM、廣告或 Cloudflare 限制作為 workaround。

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

### 依賴、可恢復交易與失敗復原

- 每個 MOD 最多宣告 `64` 個 dependency，完整 graph 最多 `512` 個節點，manifest
  讀取上限為 `256 KiB`。missing node、cycle、tamper、overflow 或無法驗證的路徑一律
  fail closed；不會以截斷、忽略或自動修正 graph 來繼續。
- Enable 前，所有 transitive dependency 必須已安裝、`pending=NONE`、已啟用且通過
  manifest／file hash／publisher trust 驗證；核心不會自動安裝或啟用 dependency。
  Disable 若會留下 enabled transitive dependent 則拒絕，不會自動 cascade 改變其他 MOD。
- Install／update／rollback／restore 會在檔案 mutation 前驗證完整 candidate graph；update
  必須維持相同 ID 與 publisher，restore 一律回到 disabled。候選即使已落盤，enable 時仍會
  重新驗證完整性、相容性、信任與 dependency readiness。
- 所有 lifecycle mutation 共用有界、跨程序 lock；`ENABLE`／`DISABLE` journal 在 start／stop
  前以 compare-and-set 提交。Supervisor 啟動只接受 Manager 已提交且 identity 完全一致的
  `ENABLE` claim；第三方 MOD 或 UI 不可直接呼叫 Supervisor 啟動入口。
- 正常 startup 與 UPDATE／ROLLBACK transaction recovery 採 dependency-first；dependency
  失敗會阻擋 downstream。未完成 toggle recovery 採 dependent-first stop；只有確認 runtime
  已停止才清除 journal 並收斂為 disabled／`NONE`，否則保留 journal 與可診斷錯誤，不得直接
  手改 SQLite。
- Rollback／restore／recovery 在移動後重新驗證 signed directory；失敗時補償回原位置。
  Restore 若補償也失敗，下次 startup 會把 identity 相符的 stranded candidate 移回 quarantine
  並保留 `REMOVE`。traversal、symlink、junction、reparse point 或 MOD root escape 會在 mutation
  前拒絕。
- Publisher trust revoke 會先停止所有 runtime，再停用該 publisher 的 exact enabled records。
  跨 publisher dependent 不會被自動改設定，但其 runtime 同樣已停止；後續 startup 會因被撤銷
  dependency 已 disabled 而阻擋。
- 降回不支援上述 recovery 的來源前，必須先以目前來源讓所有 lifecycle journal 收斂；不得刪除
  registry、backup、quarantine 或使用者資料。Executable plugin 仍預設關閉，`SAFE_MODE`／
  `BLOCKED` 規則不變。

網站功能若要整合到可信 UI，必須維持「一個網域家族一個父 MOD、額外能力拆成子
MOD」的結構，並提供 `en`、`ja`、`zh-CN`、`zh-TW` 四份完整語言資源。父 MOD
停用時子 MOD 不顯示且不可執行；網站權限、網址允許清單與 provider 不得跨群組共用。
詳細契約請見 [`site-mod-group-format.md`](site-mod-group-format.md)。

需要開發網站搜尋或下載適配器時，先依
[`adapter-sdk.md`](adapter-sdk.md) 建立 Search／Download v2 離線範例與相容
報告，再封裝進正式簽署 MOD；Adapter SDK 驗證成功不等於已受信任或可啟用。
