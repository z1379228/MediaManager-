# Development 39.0–40.0 更新紀錄

狀態：Development 39.0.7／G39-09 為
`SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`；39.0.6／G39-08 與
39.0.5／G39-07 已 source-frozen，
39.0.4／G39-06、39.0.3／G39-05、39.0.2／G39-04、39.0.1／G39-03 與 39.0.0／G39-02 已
`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`。
使用者已於 2026-07-23 分別授權 Development 39.0.5 與 39.0.6 精確範圍的 stage、
本機 commit 與 source freeze；使用者後續亦明確授權 39.0.7 production Ed25519 公開身分修正的
stage、本機 commit 與 source freeze。這不授權 push、build、建立 EXE、Testing／Stable、
Authenticode、候選簽署、發布或上傳。

## 39.0.0｜本機格式工廠第一工作包

### Goal 與範圍

在不新增雲端依賴、不自動安裝第三方程式且不覆寫來源檔的前提下，把既有、預設停用的
`media-convert` 工作區擴充為可維護的「本機格式工廠」。第一工作包聚焦已由 failing regression
證明的靜態影像缺口與 FFmpeg 失敗診斷；既有影音轉檔、轉封裝、壓縮、時間修剪、串接／切割、
字幕抽取、單工佇列、取消、`.part` 暫存、原子另存與 H.264 NVENC→CPU fallback 維持原契約。

### 已實作

- 新增 `image-png`、`image-jpeg`、`image-webp` 三個加法式 preset。
- 只接受使用者選取的本機 `.jpg`、`.jpeg`、`.png`、`.webp`、`.bmp`、`.tif`、`.tiff` 靜態影像；
  每次只輸出一幀，輸出永不覆寫來源或既有檔案。
- UI 使用「本機格式工廠（Media Convert）」名稱；GPU 選項只在既有 `video-h264` preset 可用，
  其他格式不誤示硬體加速。
- FFmpeg stderr 由背景 reader 持續排空，只保留最多 64 KiB，並在成為任務錯誤前套用既有
  secret／私有路徑 redaction；截斷時丟棄可能缺少敏感欄位名稱的首個不完整行，超限／reader
  不完整皆明示，避免大輸出造成 pipe deadlock 或敏感資訊外洩。
- FFmpeg 只允許 `file,pipe` 本機 protocol，使用 error-only log，Windows 子程序不顯示額外 console；
  輸入與輸出 leaf／直接父目錄拒絕 symbolic link 或 junction。
- Automation 的輸出副檔名 mapping 已加入三個影像 preset；內建 MOD 完整性釘選同步更新。

### 相容性、安全與限制

- `media-convert` provider ID、manifest schema、公開 request model 與既有 preset ID 不變；新功能是
  加法式且仍預設停用，沒有 UserData migration 或 breaking change。
- 只使用現有 pinned／使用者可驗證的本機 FFmpeg 邊界。不下載或執行 Format Factory、AnyRec、
  HandBrake、VLC 或其他未知安裝程式，也不根據供應商文案宣稱 binary 無惡意軟體。
- CloudConvert 不作自動 fallback；本工作包不傳送檔案、API key 或 metadata 至外部服務。
- 文件轉換需要獨立、預設停用的本機 adapter 與 macro／sandbox／檔案炸彈風險設計；未納入本版。
- DVD／CD 只可在未來另行評估使用者持有且未受保護的來源；CSS、AACS、區碼、DRM 或其他保護
  繞過永久排除。
- 圖像浮水印、GPU 能力探測、ffprobe 完成驗證、磁碟 preflight 與可恢復佇列仍需各自的
  reproducible gap、regression、rollback 與驗證；本版不宣稱已完成或實測加速。

### Risk 與 Rollback

- 主要風險是 FFmpeg build 不含指定 encoder、損壞影像、過大輸入、stderr pipe 阻塞與診斷內容
  洩漏。來源檔大小、普通檔案／linklike、輸出副檔名、本機 protocol、不覆寫與 bounded
  redaction Gate 均保留。
- 回退移除三個 preset、UI／automation mapping、stderr reader 與相符測試，並回復完整性 hash；
  不刪除來源檔、UserData 或使用者已產生的輸出，也不覆寫 Development 38.0。

### Validation

- RED：三個影像 preset 與新 `_run()` 診斷契約在實作前合計 `4 failed`。
- GREEN：擴充精準組 `69 passed, 1 skipped`；最終 conversion security 組
  `21 passed, 1 skipped`，其中使用本機 FFmpeg 8.1.2 實際執行 BMP→PNG 並驗證 PNG signature。
- 完整 `tools.run_tests` 為 `1222 passed, 7 skipped`。quality audit 為 Ruff `357`／文字 `552`；
  MOD `7 / 4`、網站 `12 / 33 / 49`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外
  compileall、SAFE_MODE verify-only 與 `git diff --check` 均通過。

## 39.0.1｜本機能力、磁碟與成品驗證

### Goal 與範圍

補足第一工作包仍缺少的執行前／執行後證據：只讀本機 FFmpeg 的 version、build configuration、
formats、encoders、filters 與 hwaccels；排程前確認預估輸出加 256 MiB reserve；FFmpeg exit 0 後
以本機 ffprobe 解析 `.part`，至少存在一條可讀 stream 才允許 atomic commit。

### 已實作的來源行為

- capability probe 逐項設有 8 秒 timeout、512 KiB 上限、Windows hidden-process flag 與既有
  redaction；失敗只記錄 error，不推測不存在的 encoder／filter／hwaccel。
- UI 預設只使用 CPU；使用者點擊「偵測本機轉檔能力」且實際觀察到 `h264_nvenc` 後才可勾選
  NVIDIA H.264。這只證明 encoder 存在，執行失敗仍沿用 CPU fallback，不宣稱速度提升。
- submit 在建立 task 前檢查磁碟；空間不足不會留下 queued task 或 partial output。
- ffprobe 只允許 `file,pipe`，JSON 上限 256 KiB、timeout 20 秒；非零退出、超限、無效 JSON、
  空 streams 或非物件 stream 均清除 `.part` 並保持既有輸出不變。
- 缺少 ffprobe 時 Media Convert 不可啟用，不以跳過驗證方式降級。

### 相容性、風險與 Rollback

- provider／preset／request schema 與輸出命名不變；`ffprobe` 是建構服務的向後相容 keyword，
  正式 bootstrap 同時注入現有本機 `ffmpeg` 與 `ffprobe`。
- 風險是不同 FFmpeg 表格旗標、probe timeout、磁碟估算誤差及合法輸出誤判；parser 同時接受實測
  FFmpeg 8.1.2 的 2 欄 filter flags 與既有 3 欄格式，磁碟 reserve 與最小 stream contract 保持保守。
- Rollback 回復 39.0.0 的 capability／preflight／ffprobe wiring；不刪除來源、UserData 或既有完成檔。

### Validation

- 初始 RED：`ConversionCapabilities` 不存在，五個新 node 無法 collection。
- conversion regression `34 passed, 1 skipped`；相關 bootstrap／catalog／dependency／version／stage
  非 UI suite `41 passed`。
- 本機 FFmpeg 8.1.2 的影音／影像 FFmpeg→ffprobe smoke `2 passed`；能力 probe 首輪揭露 filter
  flags 實際為 2 欄，修正 parser 後同一 smoke `1 passed`。
- quality audit、MOD `7 / 4`、網站 `12 / 33 / 49`、dependency lock `10`、version docs `4`、
  retained versions `5`、Repository 外 compileall、SAFE_MODE verify-only 與 `git diff --check` 均通過。
- 未執行 GUI 自動互動；UI 仍只接受使用者截圖證據，故維持 SAFE_MODE。

## 39.0.2｜Gopeed／P2P、選用語音相依與格式工廠擴充

### Goal 與範圍

完成外部 Gopeed 的本機橋接與明確 P2P handoff，修正 Speech to Text 對選用
`whisper-cli`／Speech model 的 readiness 表達，將轉檔工作區正式命名為「格式工廠」並增加固定格式。
除 Automation、Speech to Text 外，所有內建 MOD 只在全新 profile／沒有保存狀態時預設啟用；
既有使用者明確開關不被覆寫。

### 已實作的來源行為

- 新增 `gopeed-transfer` 與其 `p2p-transfer` 子 MOD，共用可信「Gopeed / P2P」工作區。
  feature 啟用與 bridge 設定分離；乾淨啟動不連線、不啟動 Gopeed、不開埠，也不恢復舊 token。
- Gopeed Bridge 只接受顯式 localhost API endpoint 與本次記憶體 token；REST response 上限 1 MiB，
  支援 info、list、resolve、create、pause、continue 與 `force=false` delete。Token 不寫 Log／設定／任務。
- HTTPS 直接檔案沿用 Direct HTTP 的明確副檔名、既有網站網域與非全域 literal IP Gate，並與 P2P
  分開驗證。P2P 只接受使用者提供的 `magnet:`／`ed2k:`，提交前解析 bounded size、
  檢查絕對儲存資料夾、單一資源容量及可用磁碟，並要求合法用途與上傳行為確認；不提供搜尋、
  自動 port forwarding 或隱含資料刪除。政策頻寬值不冒充 Gopeed 已套用的實際限速。
- Speech to Text 保持預設停用；`whisper-cli` 與 Speech model 由 hard dependency 改為 optional runtime
  dependency。MOD 可先管理，實際轉錄仍由既有 fail-closed runtime 檢查阻擋缺少的執行檔／模型。
- `media-convert` 工作區與 UI 名稱統一為「格式工廠」，新增 WebM／AVI 視訊、AAC／Opus／WAV
  音訊與 BMP／TIFF 影像 preset；全部仍由固定 FFmpeg 參數、輸出副檔名與 no-overwrite Gate 約束。
- 內建 catalog、manifests、integrity pins、Bootstrap、主視窗、MOD 管理說明與預設狀態測試同步。

### 相容性、安全與 Rollback

- 新 MOD、preset 與 optional-dependency 欄位都是加法；既有 provider／preset ID、UserData schema、
  下載佇列與 conversion request schema 不變。新預設只作用於沒有保存狀態的全新 profile。
- Gopeed、whisper-cli、模型或其他 binary 不隨 MediaManager 下載／安裝；Gopeed 遠端 endpoint、
  auto-start、browser extension、內建 P2P 搜尋與自動開埠明確拒絕。
- Rollback 移除兩個 runtime MOD／Transfer UI／新增 preset／optional readiness 與新預設，回復 39.0.1；
  不刪除外部 Gopeed task、下載資料、模型、來源檔、UserData 或既有格式工廠輸出。

### Validation

- 更新後精準非 UI 組 `120 passed, 1 skipped`；全部 114 個不含 PySide／GUI 操作的測試檔
  `1007 passed, 6 skipped in 45.27s`。最後收緊 Gopeed／Direct HTTP 共用安全邊界後，相符組
  `43 passed in 0.33s`。
- `tools.quality_audit` 通過：Ruff `361` source files、文字污染 `558` files。MOD `7 / 4`、網站
  `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、Repository 外
  compileall、精確 SAFE_MODE verify-only 與 `git diff --check` 均通過。
- 25 個含 PySide／GUI 操作的測試檔依使用者的截圖優先政策未執行；新工作區仍待人工截圖版面證據，
  因此保持 SAFE_MODE，不宣稱鍵盤／UIA／讀屏／OS 高對比或實際互動已完成。

## 39.0.3｜Gopeed 官方請求契約修正

### Goal 與範圍

修正 G39-04 的 Gopeed create／resolve request model 與官方 OpenAPI 不完全相符的可重現缺口；
不改變 localhost-only、記憶體 token、explicit action、P2P legal-use 或檔案保留政策。

### Root Cause 與修正

- 舊 request 同時送出 `url` 與相容性猜測欄位 `rawUrl`；官方 `Request` schema 設為
  `additionalProperties: false` 且只列出 `url`、`extra`、`labels`、`proxy`、
  `skipVerifyCert`，因此實際 Gopeed 可拒絕 unknown field。
- `_request_model` 現在只送必要的 `url` 與 `labels`；精確 request-body regression 同步鎖定
  direct create 與 P2P resolve 共用形狀。

### 相容性、風險與 Rollback

- 這是 wire-format 收斂，沒有 UserData、manifest、provider ID 或公開 request model migration；
  也不新增遠端 endpoint、auto-start、搜尋、自動開埠或資料強制刪除。
- Rollback 只回復 39.0.2 的 request model、回歸、版本與文件；不刪除 Gopeed task、下載資料、
  模型、來源檔或本機輸出。

### Validation

- Gopeed／P2P／Speech／格式工廠／Bootstrap／版本精準非 UI 組
  `108 passed, 1 skipped`；全部 114 個已排除 GUI marker 的測試檔為
  `1011 passed, 6 skipped`。
- quality audit 通過：Ruff `361` source files、文字污染 `558` files；MOD `7 / 4`、網站
  `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、Repository 外
  compileall、SAFE_MODE verify-only 與 `git diff --check` 均通過。
- 25 個含 PySide／QApplication／offscreen marker 的測試檔依截圖優先政策排除；未啟動外部
  Gopeed，也不宣稱 live task、實際頻寬限制、GUI 互動或外部 runtime 已驗證。

## 39.0.4｜Gopeed／P2P 有限高度版面修正

### Goal、Root Cause 與範圍

39.0.3 人工截圖證實 Transfer 工作區的四個高內容區直接加入主分頁 layout，卻沒有獨立捲動
容器；當視窗高度小於內容 size hint 時，Qt 會壓縮 card，造成標籤、欄位與按鈕重疊。
本修正只處理可信 UI 版面，不改 Gopeed API、P2P policy、token、task 或檔案行為。

### 修正、相容性與 Rollback

- 整頁內容放入 `workspaceScroll`；垂直內容 layout 使用 `SetMinimumSize`，高度不足時改由垂直
  捲軸承接，並永久停用不必要的水平捲軸。
- accessible name 與 `panel.scroll_area`／`scroll_content` 可診斷引用同步補齊；既有控制項、訊號、
  provider ID、設定與服務契約不變，沒有 migration 或 breaking change。
- Rollback 一併回復 scroll shell、純來源 regression、39.0.4 身分與文件；不刪除 Gopeed task、
  下載資料、UserData 或外部程式設定。

### Validation

- 純來源／服務 regression `12 passed`；測試沒有匯入、啟動或控制 Qt GUI。
- 全部 114 個非 UI 測試檔為 `1012 passed, 6 skipped`；quality audit Ruff `361`／文字 `558`、
  MOD `7 / 4`、網站 `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、
  Repository 外 compileall、SAFE_MODE verify-only 與 `git diff --check` 通過。
- 修正版仍需使用者截圖確認視覺結果；截圖不能證明 Tab／Shift+Tab、UIA／讀屏、Windows 高對比
  或實際 Gopeed 互動，因此保持 SAFE_MODE。

## 39.0.5｜Stable 1.0 身分與 sign-before-stage operator 修正

### Root Cause、範圍與修正

- Stable 公開身分原先沿用 Development `CORE_VERSION`，會把正式版候選錯標為 39.0.x，而不是
  獨立通道的 `1.0.0`。
- 舊 `tools.build_version` 在建置後立即 stage；Windows Authenticode 會改變 EXE bytes，因此正式
  簽署若發生在 stage／SHA-256／Ed25519 manifest 之後，所有成品完整性紀錄都會失效。
- `release_identity_version()` 現改用明確三通道 mapping，Stable 固定為 `1.0.0`。建置工具新增
  `--build-only`，保留 `.work/Stable/1.0-attempt-*` 的 EXE、wheel 與 `build-receipt.json`；receipt
  綁定 core／release／channel、clean source revision 與 wheel SHA-256。
- 外部 Authenticode 完成後，`--stage-built <work>` 只接受同一 release track、合法 attempt 名稱、
  同一 clean revision、相符 receipt／wheel，且 Stable EXE 的 Authenticode 必須為 `Valid`，才呼叫
  既有 fail-closed staging。build-only 與 stage-built 互斥，避免誤用舊單步流程。
- source-freeze 關鍵差異審查另發現 `display_version()` 的 Stable 分支仍讀取 Development
  `CORE_VERSION`，會在 UI 顯示「正式版 39.0」。新增回歸先得到 `1 failed, 3 passed`，再改用
  `STABLE_VERSION`，使公開 UI 與套件身分一致為「正式版 1.0」。

### 相容性、風險與 Rollback

- Development 核心相容版本升為 `39.0.5`；Testing 仍是 `1.1.0`，Stable 公開身分是 `1.0.0`。
  版本號只在同一通道內比較；沒有 UserData、MOD protocol 或公開 request schema migration。
- receipt 是本機 operator handoff，不是 production 簽章；正式可信度仍由 Authenticode、最終
  Ed25519 manifest、SHA-256／SBOM、copied-folder 與正式 preflight 共同提供。
- Rollback 回復 Stable identity mapping、split-phase operator、回歸、39.0.5 身分與文件；不刪除
  UserData、歷史 Version、已發布附件或未發布簽署工作目錄。

### Validation

- 封裝／版本精準回歸 `45 passed`，包含 Stable 1.0.0 身分與 UI display、build-only 不 stage、NotSigned
  fail-closed、source revision mismatch 與 receipt 後 wheel 竄改拒絕。
- 全部 114 個非 UI 測試檔為 `1019 passed, 6 skipped`；quality audit Ruff `361`／文字 `558`、
  MOD `7 / 4`、網站 `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、
  Repository 外 compileall、Version bytecode `0`、精確 SAFE_MODE verify-only 與 `git diff --check`
  均通過。
- 未實際 build、簽署、建立 Stable 或發布；production Ed25519／Authenticode 身分、人工 UI
  與候選 copied-folder 證據仍是外部 Gate，因此維持 SAFE_MODE。
- 發行整理將 Repository 首頁由 468 行歷史混列收斂為 126 行的目前 39.0.5／Stable 1.0 候選、
  安全界線與操作入口；舊 release／roadmap 與已公開附件仍由唯讀索引保存，沒有刪除或覆寫。
  此純文件更新不升修正號；version docs 與相符回歸 `19 passed`、compileall、版本稽核、
  SAFE_MODE verify-only 及 diff check 通過。

## 39.0.6｜本機歷史安全整理計畫器

### Goal、Scope 與 Priority

- **Goal**：在 Stable 1.0 已驗證並上傳後，為「本機只保留目前與上一版」提供
  可審閱、可回復、預設不刪除的精確計畫，避免人工 wildcard 誤刪 UserData 或供應鏈證據。
- **Scope**：新增 `tools.prune_local_history` 及其 regression；僅處理 `Version` 根目錄的
  legacy `X.Y` 與 `Development/`、`Testing/`、`Stable/` 精確版本資料夾。不處理
  `docs/`、GitHub Releases、UserData、`.work`、`dist` 或外部附件。
- **Priority**：P0；本機歷史已含內嵌 UserData，且使用者最終目標包含刪除舊檔，
  必須在任何不可逆操作前補上失敗優先邊界。

### Dependencies、Approach 與 Compatibility

- **Dependencies**：精確的保留版本清單、至少一個已通過 `audit_versions` 與
  `release_preflight` 的 Stable、上傳後 digest 證據，以及實際刪除的獨立明確授權。
- **Approach**：預設 dry-run；要求至少兩個唯一且精確的 `--keep`，其中一個
  必須為 publish-ready Stable。所有候選先計數與重掃，發現 UserData、symlink、junction、
  reparse point、意外根目錄內容或中途變更即整批拒絕；apply 前會重驗保留版與
  Stable preflight，並另需精確
  `DELETE-LOCAL-RELEASE-HISTORY` 確認字串。
- **Compatibility**：Development 來源身分升為 `39.0.6`；Stable `1.0.0`、Testing `1.1.0`、
  UserData schema、MOD protocol 與已保留的 release 內容均不變。

### Risk、Rollback 與 Validation

- **Risk**：刪除本質上無法從本機還原；因此工具不會推論 Stable、不自動遷移
  UserData、不刪除 Git 追蹤文件，也不將「已建立 Stable」當成「已上傳」。後者仍由
  G40 operator 在 apply 前人工核對。
- **Protected-data evidence**：唯讀盤點確認 `Version/Development/16.1/UserData` 有 6 個檔案、
  86,566 bytes；其中 5 個與目前 `UserData` 的同路徑檔案完全一致，但舊 `Logs/audit.jsonl`
  與目前檔案不同，且不是目前檔案的行前綴。它不得被合併覆寫或隨版本直接刪除；真正
  prune 前必須先保存到獨立、非 `Version` 的使用者資料／備份位置並驗證逐檔 hash。
- **Capacity evidence**：2026-07-23 唯讀快照為 42 個 release 目錄、3,983 個檔案、
  15,344,278,530 bytes。排除預計保留的 `Development/38.0` 後，現有 41 個候選合計
  3,866 個檔案、14,789,775,742 bytes；這只是清理上限，不代表可越過 Stable、UserData
  或上傳後 digest Gate。
- **Rollback**：在 apply 前只需回復工具、測試、39.0.6 身分與文件；尚未刪除任何檔案。
  apply 後只能從已核對的外部備份／上傳附件復原，因此未取得該證據與授權時不執行。
- **Validation**：RED 為缺少模組時 collection error；實作後精準回歸 `9 passed`，
  包含 dry-run 後保留版失效時 apply 拒絕且候選仍存在。
  116 個非 UI 測試檔 `1029 passed, 6 skipped`；quality audit `363 / 560`、MOD `7 / 4`、
  網站 `12 / 33 / 49`、依賴 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、
  SAFE_MODE verify-only 與 diff Gate 均通過。依截圖優先政策，24 個含 Qt／PySide GUI 操作的測試檔
  未重跑；一次誤納 GUI 的廣泛 runner 曾以兩個 stale「預設停用」測試假設失敗，測試來源已依
  canonical 內建 MOD 預設狀態校正，但未以未執行的 GUI 測試宣稱通過。本工作沒有實際使用
  `--apply`。

## 39.0.7｜production Ed25519 公開身分固定

### Goal、Scope 與 Priority

- **Goal**：把已由 operator 在 Repository 外建立的 production Ed25519 身分之非秘密
  key ID／raw public key 固定到正式驗證來源，讓候選 preflight 能拒絕錯誤或不相符的私鑰。
- **Scope**：只修改 `core/security/release_key.py` 的公開資料、Development 修正號、
  相符回歸與目前文件；私鑰、密碼、PIN、Token、Authenticode 憑證及本機私鑰路徑不進入來源。
- **Priority**：P0；空白 compiled identity 會讓所有 Stable preflight 必然 fail closed。

### Dependencies、Approach 與 Compatibility

- **Dependencies**：Repository 外私鑰已建立並限制為目前 Windows 使用者與 SYSTEM；公開值以
  既有 loader 重新導出核對。39.0.7 source freeze 已完成；後續仍依賴 build-only 授權及
  production Authenticode `Valid`。
- **Approach**：先加入 compiled identity 回歸並在空白設定取得 RED，再只編入公開 key ID／
  Base64 raw public key；測試同時要求既有 key ID regex 通過且 Base64 嚴格解碼為 32 bytes。
- **Compatibility**：Development 來源身分升為 `39.0.7`；Stable 仍是 `1.0.0`、Testing 仍是
  `1.1.0`，UserData、MOD protocol、release manifest 格式與私鑰格式均不變。

### Risk、Rollback 與 Validation

- **Risk**：編入錯誤 public key 會讓正確候選無法簽署或啟動；因此來源與 operator 私鑰已用
  既有 loader 比對 public key，簽署工具仍會在寫入 manifest 前拒絕不相符私鑰。
- **Rollback**：在 build 前回復公開身分、39.0.7 版本、回歸與文件即可；不刪除 operator 私鑰、
  UserData、歷史版本或 39.0.6 source-freeze commit。
- **Validation**：compiled identity regression 在空白設定得到 `1 failed, 6 passed`；套用公開值後
  精準 release／version `27 passed`，116 個非 UI 測試檔合計 `1030 passed, 6 skipped`。
  quality audit `363 / 560`、MOD `7 / 4`、網站 `12 / 33 / 49`、依賴 `10`、版本文件 `4`、
  保留版本 `5`、Repository 外 compileall `363`、SAFE_MODE verify-only 與 diff check 通過。
  對歷史 Development 38.0 的 preflight 已不再回報 compiled identity invalid，但仍因舊 MOD、
  manifest 缺失與 Authenticode `NotSigned` 正確失敗。尚未 build、簽署、stage、建立 Stable、
  發布或上傳。

## 參考模板判定

- [FFmpeg](https://ffmpeg.org/download.html)：主要本機引擎；能力必須依實際 build 查證。
- [HandBrake](https://handbrake.fr/news.php)：只參考 preset、queue、preview 與硬體能力工作流。
- [VLC](https://www.videolan.org/vlc/releases/3.0.23.html)：只保留未來輸出預覽／人工驗證模板。
- [Format Factory](https://www.pcfreetime.com/formatfactory/) 與
  [AnyRec](https://www.anyrec.io/video-converter/)：專有產品，只觀察分類、批次、編輯與進度 UX，
  不整合、重包或散布其程式碼、執行檔或資產。
- [CloudConvert](https://cloudconvert.com/docs/getting-started/introduction)：外部雲端邊界；不作本機
  失敗 fallback。若未來另立工作，只能是預設停用、逐次同意且清楚揭露上傳、保留、額度與成本的
  外部 MOD。

## 40.0

G40-01 現為
`BUILD WAITING / STAGED CANDIDATE + HEADLESS EVIDENCE REQUIRED`。Development 39.0.7 的
stage、本機 commit 與 source freeze 已完成；
build、EXE、Testing／Stable、
簽署、candidate staging、發布、上傳與 push 仍須各自取得明確授權。
