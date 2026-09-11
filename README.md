# MediaManager v1.0

MediaManager 是免費、無廣告、Windows 優先且本機運作的模組化媒體管理工具，
整合 YouTube、YouTube Music、Bilibili、MEGA、Direct HTTP 與本機媒體庫。
核心負責下載佇列、媒體整理、安全邊界與可信 UI；網站解析、格式轉換、語音
轉文字及自動化等功能由可個別停用的內建或第三方 MOD 提供。

MediaManager 只處理使用者有權存取的公開內容，不繞過 DRM、登入、Cookie、
Cloudflare、廣告、付費、地區或其他網站限制。

## 目前狀態

- 目前來源版本為開發版 39.0（核心相容版本 39.0.112）。
- 最新公開下載是未簽署的
  [Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)，
  對應 Development `39.0.39`。
- Development `39.0.40`～`39.0.112` 的修改尚未包含在公開 Testing ZIP。
- Testing `1.2.4` 是由本次 Development `39.0.112` source freeze 建立的本機
  未簽署候選；Testing `1.2.3` 保持不可變，兩者均未上傳或發布。
- 尚未發布已簽署的 Stable 套件；`MediaManager v1.0` 是產品顯示名稱，不代表
  Stable 已發布。

### 最近來源變更

- `39.0.112`：本機媒體庫新增使用者明確觸發的 MusicBrainz 錄音中繼資料查詢。
  查詢 MOD 在隔離程序中只連線官方 HTTPS API，限制每秒最多一個請求及 10 筆
  結果；它採 `manual` 搜尋可見性，不會混入網站聚合搜尋或背景輪詢。套用結果
  只更新 MediaManager 的本機 SQLite 標題、歌手與 MBID 標籤，不改寫媒體檔、
  檔名或內容。查詢在背景執行，介面可停止等待且由 timeout 收束已送出的請求。
- `39.0.111`：格式工廠新增 H.264 兩階段目標容量轉檔。使用背景 ffprobe
  取得來源時長，以 3% 容器餘裕計算影片平均位元率、只編碼第一音軌為
  AAC 192 kbps，完成後仍拒絕超過使用者容量上限的結果；不使用會截斷影片的
  `-fs`。另新增 EBU R128 音量標準化的 FLAC 品質優先及 Opus 容量優先格式，
  明示兩者都會處理音訊樣本，不能視為 Passthru。
- `39.0.110`：格式工廠新增明確的 Intel Quick Sync、AMD AMF 與 AV1
  NVIDIA／Intel／AMD 硬體轉檔 preset。每個 preset 都要求對應的 FFmpeg
  encoder，不在失敗時靜默改用 CPU；實際顯示卡與驅動仍於工作執行時驗證。
  FFmpeg build 能力偵測已移出 GUI thread，可取消且不會在偵測期間凍結介面。
- `39.0.109`：新增有界拖放收件流程；下載工作區只接收網址或單一 TXT／CSV，
  Direct HTTP 只接收符合既有白名單的公開 HTTPS 檔案網址，格式工廠只接收本機
  媒體，且拖入後一律先供檢查、不自動開始工作。格式工廠新增最多 20 秒的實際
  輸出試轉與開頭 15 秒快速健康檢查；兩者在背景執行、共用單一 FFmpeg 執行槽、
  可取消，試轉只寫入私有暫存目錄並在關閉預覽或服務時清除。自我檢查只回報
  這兩項手動工具的暖狀態，不會自行啟動 FFmpeg。
- `39.0.108`：修正無損字幕軌 `.mks` 在部分 FFmpeg 無法由副檔名判斷 muxer
  的問題，命令現在明確指定 Matroska；媒體庫重複確認會在採信指紋或完整雜湊
  前重新核對檔案大小與修改時間，避免掃描後同大小改寫造成誤報。Speech to Text
  的本機模型 SHA-256 與複製也移至背景執行，可在程式關閉時取消並清除暫存檔。
- `39.0.107`：手動貼入與 TXT／CSV 匯入共用新的「下載收件匣」，先列出可加入、
  工作區不符、MOD 未啟用及重複項目，再由使用者選取；新增有界
  `mediamanager://add`／`--browser-handoff` 主動交付契約，只帶入已知公開 HTTPS
  下載頁，不會自動開始下載。省資源、平衡、高速與自動模式提升為所有下載頁
  共用的全域資源模式；自動模式只在啟動時依邏輯處理器及總記憶體保守分級，
  不常駐輪詢或在工作途中跳檔。新收件匣與共用說明元件同步改善視覺階層、
  導覽捲動按鈕、鍵盤焦點及非色彩狀態文字；「工作區」選單將所有可見頁面
  分成下載、搜尋與媒體、工具、自動化、官方工具及其他，分頁過多時仍可直接
  跳轉。媒體庫以大小、首尾指紋與完整 SHA-256 分層確認重複檔案；完整檢查在
  背景執行、可取消且不會自動刪除。
- `39.0.106`：補強 onefile／onedir 比較器的執行安全。證據輸出路徑會在 build
  前及寫入前各驗證一次；Windows 測量程序先以 suspended 狀態加入具
  kill-on-close 的 Job Object 才開始執行，逾時或設定失敗會收容並清理完整
  程序樹。隔離實驗已完成；本機 onedir 啟動較快，但檔案數與總容量明顯增加，
  尚未取代正式 onefile 配置。
- `39.0.105`：新增隔離的 onefile／onedir PyInstaller 配置比較器。正式發行建置
  仍強制使用 onefile；比較器預設只列出計畫，必須明確指定 `--execute` 才會
  在 Repository 外建立兩種原型、量測啟動／驗證／Provider Host、核對完整樹
  SHA-256 並執行複製資料夾 smoke；實驗由 `39.0.106` 完成並保留比較證據。
- `39.0.104`：YouTube 播放清單新增預設關閉的「大型清單快速模式」，最多仍
  載入 500 項；使用者選取後才啟用 yt-dlp lazy playlist，並明示結果不是完整
  總數且不支援隨機或反向排序。未選取時及其他網站維持原有契約。
- `39.0.103`：YouTube 下載新增由可信核心管理的省資源、平衡、高速與自動
  效能設定；核心依全域同時工作數配置有界片段併發，覆寫外來同名選項，
  切換後同步所有下載頁。進行中或暫停中的工作不允許切換設定，避免新舊
  配額重疊；不使用實驗性 HTTP chunk 或網站限制規避參數。
- `39.0.102`：MEGA、Direct HTTP 與 Gopeed 工作表以資料簽章跳過相同快照，
  有變動時在批次套用期間暫停中間 repaint；大量表格基準顯示逐 cell 重用較慢，
  因此未採用該候選或提前遷移 model/view。隱藏且無工作時維持 10 秒低頻檢查，
  關閉頁面會停止既有 timer。
- `39.0.101`：YouTube、Bilibili、網站搜尋及播放清單共用主視窗層級的
  有界縮圖服務；每頁只請求目前可見列與少量前後緩衝，離開分頁會取消
  該頁尚未完成的請求，返回時再補載，共用快取不會被單一頁關閉清空。
- `39.0.100`：主視窗只在啟動時建立目前的 YouTube 工作區；Bilibili、
  網站搜尋、本機媒體庫與已啟用的選用工作區保留分頁 shell，第一次
  開啟時才匯入模組並建立介面，之後保留同一物件與使用者輸入。
- `39.0.99`：將重複的下載 RUNNING 進度通知合併為每工作的最新快照，
  並保留完成、失敗、暫停與取消等狀態立即送達；音訊與影片播放元件
  改為首次預覽才建立，關閉或停止後釋放媒體來源與 Qt 物件；
  來源模式的 Provider／Plugin Host 明確使用 Python `-B`，完整測試後不會
  在 Repository 留下位元碼快取。
- `39.0.98`：將 version、verify、Provider 與 Plugin 等非圖形角色分流到可信 UI
  匯入前，並新增隔離使用者資料、禁止網路與可見 UI 的啟動資源基準工具；
  pytest 子程序不再把 Python 位元碼快取寫回來源樹。
- `39.0.97`：新增低資源背景待機、可選的關閉至系統匣／完全結束，以及由使用者
  明確啟用的 Windows 登入後背景啟動；閒置分頁降低輪詢頻率，Automation 在
  沒有規則時不再週期喚醒，剪貼簿改由變更事件觸發。快速最小化／還原不會
  誤留在待機狀態，背景期間完成的預覽準備也不會自行開始播放。
- `39.0.96`：移除第三方 MOD 驗證訊息中的硬編碼 `core 3.0`，並讓 GitHub
  Quality workflow 統一使用具 60 秒逾時及隔離暫存目錄的專案測試 runner。
- `39.0.95`：啟動時直接顯示主畫面，不再自動彈出首次 MOD 設定或依賴環境
  視窗；相關功能仍可由主畫面的按鈕手動開啟。
- `39.0.94`：強化 H.265 Main10 NVENC／Opus Passthru MKV preset 的輸出契約
  驗證與失敗清理。
- `39.0.90`～`39.0.93`：新增影像浮水印、YouTube Music 搜尋路徑與下載後
  本機轉換 preset。
- `39.0.13`～`39.0.89`：改善多來源搜尋、分頁、去重、Unicode 比對、相似音樂
  排序、失敗隔離及第三方 Search v2 MOD 契約。

完整技術紀錄請見
[Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)。

## 快速下載與啟動

1. 從 [Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
   下載
   [`MediaManager-Testing-1.2.2.zip`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip)
   與
   [`MediaManager-Testing-1.2.2.zip.sha256`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip.sha256)。
2. 將兩個檔案放在同一資料夾，使用 PowerShell 核對 SHA-256：

   ```powershell
   Get-FileHash -Algorithm SHA256 .\MediaManager-Testing-1.2.2.zip
   Get-Content .\MediaManager-Testing-1.2.2.zip.sha256
   ```

3. 確認兩者雜湊相同後，將 ZIP 解壓縮至新的空資料夾。
4. 進入含有 `MediaManager.exe` 的資料夾並雙擊啟動，不需要另外安裝 Python。

Testing 1.2.2 是未簽署測試版，Windows 可能顯示無法驗證發布者的警告。請只從
上述 GitHub Release 下載並核對雜湊，不要關閉 Windows 安全功能。建議下載完整
ZIP，不要單獨下載 EXE；ZIP 不包含任何使用者資料。

一般雙擊啟動會使用 `%APPDATA%\MediaManager`、`%LOCALAPPDATA%\MediaManager`
與 `Downloads\MediaManager`，不等同於 `--portable` 資料模式。詳見
[免安裝自包含 ZIP 說明](docs/self-contained-zip.md)。

## 主要能力

- YouTube／YouTube Music 公開搜尋、批次工作與相似音樂候選。
- 下載收件匣統一檢查手動網址與 TXT／CSV；瀏覽器可用明確的交付參數開啟
  正確下載工作區，仍需使用者確認格式與加入佇列。
- Bilibili、MEGA、Direct HTTP 及網站矩陣中明列的獨立工作區。
- 本機媒體庫（含可取消的完整 SHA-256 重複確認）、原子寫入下載佇列、歷史、
  取消、重試與恢復。
- 背景待機：最小化或關閉至系統匣時暫停不可見 UI 輪詢；右下角可改為完全
  結束，設定選單可選擇 Windows 登入後自動在背景啟動。
- 格式工廠：使用本機 FFmpeg 處理影片、音訊、影像、字幕、切割、串接、壓縮、
  固定位置影像浮水印及 H.265 Main10 NVENC／Opus Passthru MKV；可在背景檢查
  單一來源的音訊／字幕軌，選取後以 Matroska stream copy 輸出並驗證 codec 與
  封包雜湊，不重新編碼。
- Gopeed Bridge／P2P Transfer：只連接使用者自行啟動的 localhost Gopeed API。
- 選用 Speech to Text 與 Automation；Speech to Text 可另匯入明確分類且
  SHA-256 驗證的 VAD 模型，只有背景偵測到 whisper-cli 同時支援 `--vad` 與
  `--vad-model` 才能手動啟用，預設仍關閉。未安裝不影響核心功能。
- schema v2 第三方 MOD、Ed25519 發布者簽章、最小權限、受控程序及宣告式 UI。

實際可用能力以程式內的 MOD 管理、
[依賴檢查](docs/dependency-health.md)與
[網站主機清冊](docs/site-host-inventory.md)為準。外部工具名稱不表示
MediaManager 會自動安裝、捆綁或承諾其全部功能。

## 從原始碼執行

必要條件：

- Windows 10／11 x64。
- Python 3.14 以上。
- Git。

在 PowerShell 執行：

```powershell
git clone https://github.com/z1379228/MediaManager-.git
Set-Location .\MediaManager-
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[ui]"
.\.venv\Scripts\python.exe -B .\main.py --verify-only
.\.venv\Scripts\python.exe .\main.py
```

開發者若需要測試工具，將安裝命令改為：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui,dev]"
```

`main.py` 是正式入口；`desktop.py` 僅為舊版相容轉接。`--verify-only` 只驗證
核心完整性。啟動 UI 後，可點擊主畫面的核心／選用 MOD 工具狀態按鈕開啟
「執行環境」，再按「重新檢查」確認 yt-dlp、FFmpeg、JavaScript runtime 等
外部工具。程式只顯示缺少項目，不會未經確認自動安裝。

完整的更新、移除及排錯流程請見 [INSTALL.md](INSTALL.md)。

## 安全與資料界線

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站存取限制。
- Cookie、Token、私鑰、production 憑證及個人資料不得寫入 Repository 或 Log。
- URL、檔案、MOD manifest、IPC 與外部程序輸出一律視為不可信。
- 新安裝或更新的第三方 MOD 預設停用；信任發布者與啟用 MOD 是兩個獨立決定。
- 宣告式 MOD UI 不執行外部 HTML、Qt 物件或任意腳本。
- Development、Testing 與 Stable 的身分、雜湊、簽章及發布 Gate 不可互相冒用。

第三方 MOD 作者請從 [MOD-DEVELOPMENT.md](MOD-DEVELOPMENT.md) 開始，並參考
[第三方 MOD 開發指南](docs/mod-developer-guide.md)、
[MOD 套件契約](docs/mod-package-v1.md)與
[簽章流程](docs/release-signing.md)。

## Repository 結構

- `core/`：安全、下載、設定、儲存、媒體庫與 MOD 生命週期。
- `trusted_ui/`：PySide6 可信 UI。
- `contracts/`：核心與 MOD 共用的版本化資料契約。
- `mod/builtin/`：可個別啟用或停用的內建 MOD。
- `plugin_host/`：外部可執行 MOD 的受控程序入口。
- `tests/`、`tools/`：回歸測試、品質、版本與發行工具。
- `docs/`：目前有效的規格、狀態與維護文件。
- `Version/`：不可覆寫的 Development／Testing／Stable 產物。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m tools.quality_audit
.\.venv\Scripts\python.exe -m tools.run_tests
.\.venv\Scripts\python.exe -m tools.audit_mod_groups --root .
.\.venv\Scripts\python.exe -m tools.site_quality_audit --root .
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_version_docs
.\.venv\Scripts\python.exe -B .\main.py --verify-only
git diff --check
```

Repository 測試應使用 `tools.run_tests` 的 Repository 外隔離暫存目錄；不得讓
raw pytest 回退到 Repository 根目錄。

## 文件

- [文件索引](docs/README.md)
- [下一次 Development 資源與 MOD 效能計畫](docs/performance-mod-optimization-plan.md)
- [安裝與啟動](INSTALL.md)
- [目前專案狀態](docs/project-status.md)
- [Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)
- [下載工作契約](docs/downloads-v1.md)
- [第三方 MOD 開發指南](docs/mod-developer-guide.md)
- [版本與發布政策](docs/version-layout.md)
- [免安裝自包含 ZIP](docs/self-contained-zip.md)

目前文件索引只保留仍有效的下一次更新計畫；已結案 roadmap、過期候選與逐版
重複日誌由 Git 歷史及 GitHub Releases 的不可變附件追查。已公開的 EXE、
checksum、release metadata 與 tag 不得刪除或覆寫。

## License

[MIT](LICENSE)
