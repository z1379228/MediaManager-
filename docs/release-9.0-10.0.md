# MediaManager 開發版更新紀錄 9.0～10.0

## 10.0

- `release-info.json` 升級為 schema 2，綁定來源 SHA-256 指紋、Git revision、建置 ID
  與工具 schema；來源指紋採固定路徑、檔案數量及大小上限，不掃描版本附件或使用者資料。
- 正式候選 evidence 升級為 schema 2，必須同時符合開發版版本、build ID、來源指紋、
  工具 schema 與實際 `SHA256SUMS.txt` digest；舊布林證據或不同建置一律拒絕。
- 版本稽核同時相容既有 schema 1 歷史附件與新的 schema 2，不改寫舊版本雜湊；Stable
  簽章檔案集合明確納入 wheel、`release-info.json` 與 `SHA256SUMS.txt` 作為簽章錨點。
- 10.0 開發版維持 `SAFE_MODE`，不包含 production 私鑰或憑證，也不建立 Stable 版本。

### 10.0 驗證結果

- Ruff 全專案檢查通過；Pytest 667 項通過，2 項因目前 Windows 帳戶無法建立
  symlink 而跳過，沒有功能性失敗。
- `tools.audit_mod_groups`：4 個網站群組與每組 4 個語言檔通過；網站品質矩陣離線
  核對 6 個網站與 12 個能力項目通過。
- PowerShell 污染掃描核對 710 個明確來源／文件檔案：UTF-8、merge marker、工具殘留與
  內嵌 BOM 均通過。
- copied-folder smoke：`--version`、`--portable --verify-only`、
  `--portable --headless` 均以 exit code 0 完成；audit 記錄為預期的 `SAFE_MODE`，
  沒有啟動外部 MOD。
- `Version/Development/10.0` 共 72 項 SHA-256 稽核通過；`MediaManager.exe`
  SHA-256 為 `E1304228792C33F56D6624313DEB1C73DAE4800C73E02B3E9DBB96DB31837EC1`。
- Authenticode 實際狀態為 `NotSigned`；production Ed25519 身分也未設定，因此本成品
  只能作為 Development／`SAFE_MODE`，不得標記或包裝為 Stable。

## 9.9

- MOD 管理新增可信核心的「自我檢查」頁面；只有使用者按下按鈕才檢查編目、registry、
  父子路由、選用工作區、內建 MOD 初始化、安全模式、暖依賴快照與發行資訊。
- 結果分為通過、警告及阻擋，提供穩定 `remediation_id` 與去識別 JSON 匯出；報告不含
  本機絕對路徑、依賴工具路徑或來源指紋。
- 自檢不連網、不重新探測依賴、不啟動 provider／FFmpeg、不執行 Pytest，也不自行建立
  暫存檔；原「製作中」清單已移除 Self Check 項目。

## 9.8

- Facebook、MEGA、Media Convert、Speech to Text 與 Automation 選用分頁改用同一個
  `OptionalWorkspaceManager` 建立、移除、停止與釋放，避免各分頁各自維護重複流程。
- Event Bus 支援去重訂閱與解除訂閱；下載工作區關閉時會解除語言與 MOD 狀態 callback，
  並取消未完成縮圖工作，降低反覆開關 MOD 後的殘留事件。

## 9.7

- 依賴快照加入 PATH 與必要工具大小／修改時間的有界指紋；未變更時共用既有結果，
  手動重新整理或明確 invalidation 才重新探測。
- `peek()` 只讀暖快照，不啟動程序、不雜湊大型媒體或模型內容，供低耗用診斷使用。

## 9.6

- 集中 yt-dlp、yt-dlp EJS、JavaScript runtime、FFmpeg、MEGAcmd、whisper-cli 與語音模型
  的依賴狀態，按 16 個內建 MOD 分別產生 readiness 與缺失項目。
- 主視窗與環境檢查視窗共用同一快照服務，避免每次開啟介面重複啟動版本探測程序。

## 9.5

- 新增型別化 `BuiltinModDescriptor` 編目，集中 16 個內建 MOD 的種類、預設狀態、控制
  位置、父 MOD、選用工作區及依賴；Bootstrap 與可信 UI 從同一來源產生清單。
- 安全權限 allowlist 與內建 provider 固定雜湊仍保持獨立，避免呈現層編目意外放寬權限。

## 9.4

- 跨 MOD 搜尋若明確指定不存在、初始化失敗或未註冊搜尋能力的來源，會立即回報來源
  不可用；指定停用來源則回報停用，不會改查 YouTube 或其他網站。

## 9.3

- 聯合搜尋對每個已選來源採有界 page size，先取得各來源結果，再以穩定 round-robin
  去重合併；第一個來源不再能獨占整個結果上限。
- 單次最多選擇 16 個來源、每來源最多收集 20 筆、總結果最多 50 筆，維持資源上限。

## 9.2

- 新增彼此隔離、預設停用的 Facebook 與 MEGA 主 MOD；啟用後才在主畫面建立各自
  下載工作區，停用時立即移除工作區並取消該 provider 擁有的下載工作。
- Facebook 只接受受限的公開 `watch`、`video.php`、`reel`、`videos` 與 `fb.watch`
  網址；可讀取公開標題、格式與 `fbcdn.net` 縮圖，下載由獨立 yt-dlp provider 分流。
  不接收 Cookie、帳密、私人頁面、任意貼文路徑或登入內容。
- MEGA 只接受帶完整解密片段的現代 `mega.nz/file/...#...` 與
  `mega.nz/folder/...#...` 公開分享。分析會顯示本機檔案／資料夾縮圖及 `mega-get`
  狀態；9.2 只把公開檔案交給官方 MEGAcmd，資料夾分享僅辨識並明確拒絕下載。
- MEGA share key 不進入分析標題、一般狀態或錯誤文字；完整連結只交給使用者明確
  啟動的本機 provider／官方 `mega-get` 程序。兩個新 MOD 均不加入 `generic-ytdlp`。
- Facebook、MEGA 各自提供 `group.json`、四語言 `locales/`、最小權限 manifest 與
  SHA-256 固定雜湊；MOD 管理不再把兩者列為「製作中」。
- 版本改為 Development 9.2.0；不建立或覆寫 Stable 版本。

### 9.2 已知限制

- Facebook 是 Development 階段的公開頁面相容能力，不代表 Meta 官方支援；網站改版、
  地區、登入或權限限制會直接失敗，不會匯入瀏覽器 Cookie 或繞過限制。
- MEGA 下載需要使用者已安裝的官方 MEGAcmd 且核心能找到 `mega-get`；未偵測到時仍可
  本機辨識網址與類型，但下載保持 fail-closed。
- MEGA 公開資料夾、多檔選擇、帳號同步、上傳、備份與配額繞過不在 9.2 範圍。

### 9.2 驗證結果

- Ruff 全專案檢查通過。
- Pytest：652 項通過、2 項因目前 Windows 帳戶無法建立 symlink 而跳過；其中
  Facebook／MEGA provider、網址路由、MOD 群組、縮圖、Bootstrap 與可信 UI 的目標
  測試為 135 項通過。
- `tools.audit_mod_groups`：通過，驗證 4 個網站群組與每組 4 個語言檔。
- copied-folder smoke：`--version`、`--verify-only`、`--headless` 均以 exit code 0
  完成；測試副本已清除，沒有把 Portable 使用者資料寫入正式成品資料夾。
- `Version/Development/9.2`：72 項 SHA-256 稽核通過；Facebook／MEGA 的 provider、
  manifest、group 與四語言檔均包含在版本資料夾及 checksum。`MediaManager.exe`
  SHA-256 為 `FFFE15809EEB6BD7A43D5CA7EAD54E314DCE10E01F450C473313E6B3239C3D5D`。
- Development 9.2 仍維持 `SAFE_MODE`，不是 Stable 1.0；未建立 Stable 目錄或附件。

## 9.1

- YouTube 與 Bilibili 改為可驗證的父 MOD／子 MOD：主 MOD 未啟用時不顯示子 MOD，
  停用主 MOD 會同步停用子 MOD並阻止背景殘留狀態。
- YouTube 下載工作區與 Bilibili 下載工作區完全分頁、分 URL 路由、分搜尋交接；錯誤
  網域無法加入佇列，Bilibili 搜尋不再出現在未啟用的 Bilibili 主 MOD 下。
- 內建網站 MOD 加入受 SHA-256 保護的 `group.json` 與四語言 `locales/`；核心語言
  `en`、`ja`、`zh-CN`、`zh-TW` 會同步到工作區、MOD 管理與搜尋子 MOD。
- 新增 `tools.audit_mod_groups`，檢查父子覆蓋、四語言完整性、provider 身分、網路權限
  與搜尋網站家族，禁止跨網域 provider 偽裝成已分離。
- `generic-ytdlp` 僅保留為預設停用的舊 Beta 相容項；新網站必須各自建立主 MOD，
  不得再加入多網域聚合 provider。
- 9.1 使用新的 `Version/Development/9.1` 資料夾，不覆寫 Development 9.0。

### 9.1 驗證結果

- Ruff 全專案檢查通過。
- Pytest：632 項通過、2 項因目前 Windows 帳戶無法建立 symlink 而跳過。
- `tools.audit_mod_groups`：通過，驗證 2 個網站群組與每組 4 個語言檔。
- copied-folder smoke：`--version`、`--verify-only`、`--headless`、凍結後 MOD 載入及
  YouTube Music 播放清單網址解析皆通過。
- `Version/Development/9.1`：58 項 SHA-256 稽核通過；`MediaManager.exe` SHA-256 為
  `D6EC56BA2BD54CC76530040C17389999320F3774110CB9B3733F7006AD244C14`。
- 發布 preflight 仍因缺少 production Ed25519 發布身分與 Authenticode 簽章而阻擋；
  9.1 僅為 Development／`SAFE_MODE` 成品，不是 Stable 1.0。
- 完整測試跳過、環境限制與正式發布阻擋記錄於
  [`release-9.1-known-issues.md`](release-9.1-known-issues.md)。
