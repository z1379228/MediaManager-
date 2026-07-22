# Development 37.0–38.0 更新紀錄

狀態：Development 37.0 source-only Exit Gate 已完成，判定為 `EVIDENCE READY / NO CLAIM`；
Development 38.0 source freeze 與 SAFE_MODE 未簽署候選包已由實際 post-build 稽核通過且
不可覆寫；38.1.16 是 38.x 最後的 source-only 節點，狀態為
`SOURCE VALIDATED / PACKAGING INPUT HARDENED / NO PACKAGE / SAFE_MODE`，尚未 stage、commit、freeze 或 build。
目前 Development 39.0.0 的變更另見 [39.0～40.0 更新紀錄](release-39.0-40.0.md)。本文不是
Testing／Stable 宣告、正式簽署證據或原生 crash 已修復聲明。

## 37.0｜去識別原生／provider 證據邊界

- 新增 strict `DiagnosticEvidenceV1`；只接受相同 self-check `run_id`、component、UTC 時間、
  32-bit exit code、ASCII module basename、faulting offset 與選用的本機 artifact SHA-256。
- reader 拒絕 unknown field、路徑化 module、非 UTC 時間與非 canonical code；writer 沒有自由文字、
  URL、Cookie、token、stack、dump path 或 dump bytes 欄位。Self-check schema 仍為 1，舊 consumer
  可忽略 additive `diagnostic_evidence`。
- 共用 redaction 現在遮罩已驗證的 Authorization／Cookie header（含 quoted key）、MEGA key、exact
  secret query、HTTP(S) URL userinfo 與 absolute private path；一般 key/value 增加左界，避免把
  `not_token` 誤判為 token。沒有把這組 corpus 推廣為任意自由文字的絕對完整遮罩保證。
- 所有診斷文字先去識別、移除不安全 control／bidi，再依 UTF-8 bytes 截斷。Provider stderr
  與 structured failure 在形成可信錯誤前處理；DownloadQueue 在把錯誤寫入或還原持久狀態前再做
  防禦性處理。Queue restore 以單一 bounded binary open 讀取，transient OSError 最多重試 3 次。
- Provider 無結果退出保留原 exception 與失敗語意，只附加 bounded `stdout_eof`／
  `handoff_deadline`、exit code 與 reader-complete metadata；未新增 retry，也未放寬 assertion。
- Self-check 最終 serialization 再做一次 field redaction／bound，匯出改用同目錄唯一 owned temp、
  UTF-8 1 MiB 上限及原子 replace；失敗只清除本輪 temp，保留原 destination。
- [原生崩潰去識別證據 Runbook](native-crash-evidence-runbook.md) 明定只人工抄錄 allowlisted WER
  metadata。不得自動搜尋、解析、保存或上傳 dump；若使用者明確選定本次新 dump，只在本機計算
  SHA-256 並抄錄 hash。

## Compatibility、Risk 與 Rollback

- Provider protocol、ProviderFailure taxonomy、manifest、capability、UserData 與 self-check
  `schema_version` 不變；新增 evidence 是頂層 additive output，strict record 自帶 schema 1。
- `run_id` 只代表 evidence bundle correlation，不代表 crash process trace。`0x80000003` 仍未重現，
  沒有 WER module／offset 或 root cause，故只能標記 `EVIDENCE READY / NO CLAIM`。
- 回退可移除 evidence contract／附加欄位、exit metadata 與新 runbook，並回復 redaction／原子 writer；
  不遷移、刪除或重寫 UserData，也不接觸原始 dump。

## 驗證與限制

- failing regression 先得到 redaction／stderr／queue persistence／exit metadata `4 failed, 78 passed`；
  evidence contract 與 atomic writer 在實作前均 collection error。獨立審查後又以 exact failures 關閉
  duck-type evidence、quoted／structured secret、URL userinfo、provider stderr drain 與 queue transient
  restore 路徑；最終 G37 相關 5 檔 targeted group 為 `112 passed`。
- 完整 Repository 第一次於 history provider 間歇空輸出得到 `1 failed, 1276 passed, 7 skipped`；壓力
  取證為 `stdout_eof / exit_code=1 / reader_complete=true`，但 root cause 仍未知且未加入 retry。第二次
  於 queue restart 讀取競態得到 `1 failed, 1276 passed, 7 skipped`，deterministic PermissionError
  regression 驗證舊 restore 會錯誤回傳空 queue，修正後最終為 `1278 passed, 7 skipped`。
- Ruff／文字污染 `365 / 570`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、scoped compileall、Version `.pyc` 零污染與 `git diff --check` 均通過。直接 Ruff 另對
  保留且不可讀的未知 `tmpk89a7j7y` 回報 access-denied warning；authoritative quality audit 明確掃描
  `365 / 570` 並通過，未刪除或 broad-ignore 該使用者／來源未知目錄。
- G37 Exit Gate 完成當時未取得 stage、commit、source freeze、build、EXE、Testing／Stable、
  簽署、發布、push 或外部／人工操作授權；此為歷史判定，不否定後續取得的 Development 38.0
  明確授權，且全程維持 `SAFE_MODE`。

## 38.0

此節是 `BASELINE FROZEN / PACKAGE BUILT / G38-01 MANUAL REVALIDATION BLOCKED / SAFE_MODE` 歷史基線；
G39-01 measurement baseline 已完成為 `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`，目前沒有
`ACTIVE / IN_PROGRESS` 工作。2026-07-22 source-only `python -B main.py --verify-only` 已 exit 0 並
精確輸出 `MediaManager security mode: SAFE_MODE`；G40-01 仍等待逐項授權與 staged verify／headless 證據。
不需人工 UI 的無頭基線已於 2026-07-19 透過兩組精準 `tools.run_tests` 重驗，合計
`58 passed, 0 skipped`。最新 Quality audit `366 / 571`、MOD group audit `8 / 4` 與 site audit
`13 / 42 / 56` 均 PASS。後續 source review 找到兩個 material P1：可聚焦 tree 的預設 outline
被移除且無替代指示，安全 badge 的 explicit accessible name 則未包含實際狀態。兩項都先以
failing regression 重現，再於 tree focus 提供 2px 高對比 border，並讓 badge 名稱與
description 暴露狀態／原因；相關 UI 組 `12 passed`，post-fix 完整 Repository
`1279 passed, 7 skipped`。

使用者提供的 Development 37.0 AniGamer 截圖只作為 pre-fix baseline。它記錄兩個獨立安全降級：
本機 Qt WebEngine 缺少 H.264／AAC 或可用 HLS／MSE 播放路徑，以及集數 provider 遇到官方
403／瀏覽器驗證時顯示空表與手動官方單集網址 fallback。新增的完整回歸固定「選取作品→
browser-verification failure→貼上 canonical `animeVideo.php?sn=49944`→建立單集列／作品 context」；
既有 production path 無需修改即通過，故判定為 `EXPECTED LIMITATION / NO NETWORK POLICY CHANGE`。

G38 的最小 UI 修正只把既有「在系統瀏覽器開啟」主操作移到 WebView 上方，保留 primary、
stable control ID 與 accessible name；fake WebEngine offscreen regression 固定其可見順序。
AniGamer targeted suite 為 `60 passed, 1 skipped`，本輪完整 Repository Gate 為
`1281 passed, 7 skipped`。本變更未下載 codec，未匯入 Cookie、攔截播放
串流／媒體端點，亦未繞過 DRM、廣告、登入、Cloudflare／瀏覽器驗證、付費或地區限制；因此
不得宣稱內嵌播放能力已修復。

目前已有 38.0 material delta，核心身分已同步為 `38.0.0`；人工 Gate 仍未完成。使用者已明確授權
本次 stage、本機 commit、Development 38.0 source freeze，以及一次 Development 38.0 SAFE_MODE
未簽署候選包。source freeze commit 為
`6534e3f5ebcc3e3c459a34a335e2b176b2cd1107`，產物已建立於 `Version/Development/38.0`。

### 38.0 封裝證據（2026-07-19）

- `release-info.json` 為 schema/tool schema 3，`core_version`／`release_version` 均為 `38.0.0`，
  channel／track／folder 為 `development / Development / 38.0`；`source_revision` 精確等於上述
  source freeze，source fingerprint 為
  `4438b8f606a6e11b1d1d898b631fbd590ffce5fbdbd34fb1d9533ccc0144d8ce`。
- `tools.audit_staged_runtime` 為 `valid=true / checked=6`；Deno `2.9.2`、FFmpeg／ffprobe
  `8.1.2` 與三份授權／說明檔均通過 pinned SHA-256 policy。
- `tools.audit_versions` 驗證 Development 38.0 的 116 筆 checksum 全部通過。`MediaManager.exe`
  為 249,897,780 bytes，SHA-256
  `ed94e16da81e7f62008dc07910bff3bc4c3419e1ca39ab05c391d0ac59a53b8c`；wheel 為
  920,186 bytes，SHA-256 `d017d263fecf05dd86ff04adb3a62b5b92aad63890431e9e6aed42a1e288d77d`。
- disposable copied-folder smoke 依序執行 `38.0 → 32.1 → 38.0`；9 個 `--version`、
  `--portable --verify-only`、`--headless --portable` 命令皆 exit 0，且
  `rollback=true / source_unchanged=true / process_tree_safe=true`，attempt 已清除。
- Authenticode 為 `NotSigned`。copied-folder 報告沒有保存精確 SAFE_MODE stdout，因此本證據不完成
  G40 Exit Gate；也不替代 G38 的 940×620、四語、NVDA／UIA 與 OS 高對比人工矩陣。

真實 940×620 全工作區、Tab／focused widget、NVDA／讀屏、Windows OS 高對比、四語逐頁裁切與
SAFE_MODE／provider blocker 實際朗讀，必須取得相符環境與明確人工操作授權。未滿足前保持
`MANUAL REVALIDATION BLOCKED`；不得以 headless exit 0 代替。UI 驗證採截圖優先且禁止自動
互動；截圖只能支持可見版面、裁切、文字、色彩與可見焦點，不能證明 Tab／Shift+Tab、UIA／
NVDA／讀屏或 Windows OS 高對比行為。

## 38.1.x 歷史與退役｜G38-02 動畫瘋整合

Development 38.0 仍是不可覆寫的已封裝基線；本節記錄尚未 stage、commit、source freeze 或
build 的 38.1.x 來源差異，不宣稱新候選已建立。38.1.0 是首次來源基線；基線後每個 material
程式修正依序使用 38.1.1、38.1.2、38.1.3、38.1.4、38.1.5、38.1.6、38.1.7、38.1.8、38.1.9、38.1.10、38.1.11、38.1.12、38.1.13、38.1.14，純文件、截圖或證據更新不升版。
38.1.13 已標記 `SOURCE VALIDATED / SUPERSEDED BY 38.1.14 / NO PACKAGE`。38.1.14 後續由
38.1.15 取代；G38-02 的最終狀態為
`CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`。本節其餘 38.1.0～38.1.14
內容只保存歷史工程證據，不再具有 execution ownership。

- 優先順序改為官方頁播放與作品／集數讀取，之後只在官方授權契約明確時評估離線影片，最後
  才評估官方公開彈幕。
- 系統瀏覽器是主要播放成功路徑並使用瀏覽器自己的登入工作階段；內嵌 Qt WebEngine 仍是選配
  相容路徑。官方頁可自行播放，但 MediaManager 不使用 request interceptor、DevTools、service
  worker 或腳本擷取 M3U8、金鑰、媒體片段或播放串流。
- 新增的動畫瘋 session Cookie 僅接受使用者主動貼上的 request-header body，嚴格限制大小與
  格式，拒絕 Cloudflare 驗證狀態；只在程序記憶體中送往 `https://ani.gamer.com.tw` 精確主機
  的目錄與集數 provider。它不進設定、佇列、歷史、離線索引、argv、環境變數、URL 或 Log。
- 停用動畫瘋父 MOD、使用者清除、關閉工作區或程式結束會先取消相關 provider 工作再撤銷
  Cookie。Python／Qt 的暫時副本只承諾不持久化與邏輯清除，不宣稱能從 pagefile 或 crash dump
  鑑識抹除。
- 未找到官方允許保存的非 DRM 媒體來源時，離線影片保持
  `NO AUTHORIZED MEDIA SOURCE / BLOCKED`；未找到官方公開彈幕契約時保持
  `DEFERRED / NO AUTHORIZED PUBLIC CONTRACT`。
- 播放器、瀏覽器與 Qt WebEngine 暫存不會轉作下載緩存。若未來官方契約明確提供可保存的
  非 DRM 來源，只能由下載器寫入 MediaManager 自有、具原子暫存與雜湊驗證的內容快取，再供
  本機播放器重用；本節僅記錄設計邊界，不代表下載功能已實作或獲授權。
- 來源側 G38-02 非 UI 回歸於 2026-07-19 使用 Repository runner 與唯一、Repository 外 temp root
  完成，結果 `176 passed`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall 與 diff check 均通過。
- 2026-07-20 已同步 38.1.0 來源／metadata／文件身分並讓 Development UI／CLI 顯示完整修正號；
  版本、entrypoint、build 與文件稽核回歸 `37 passed`，CLI 實際輸出
  `MediaManager 開發版 38.1.0`。未 stage、commit、freeze、build 或修改既有 38.0 產物。
- 上述證據未使用真實 Cookie、未連線動畫瘋，也未啟動或控制 GUI，因此不代表官方播放或真實
  Cookie 工作階段已成功。P1-A 與真實 P1-B 仍需使用者人工結果；完整 Repository suite 含 GUI
  自動互動案例，依本輪驗證限制未執行。

### 38.1.1｜不相容內嵌頁 fail closed

- Root Cause 是 capability 已判定 `UNSUPPORTED`／`UNKNOWN` 後只把系統瀏覽器 fallback 設為預設，
  未停止或隱藏 WebView，因此使用者仍會看到誤導的黑色官方播放器錯誤。
- 新增純 `WebEngineMediaPresentation` 三態 policy；只有 `SUPPORTED` 顯示內嵌頁，其餘狀態及
  load／probe timeout、load failure、renderer termination 都停止並隱藏 WebView，同時保留使用者
  明示觸發的系統瀏覽器主操作。
- 本修正沒有自動開啟外部瀏覽器、注入 Cookie、安裝 codec、攔截播放串流或改變離線下載邊界。
  真實系統瀏覽器播放仍為 `LIVE WAITING`，不得宣稱內嵌播放能力已修復。
- 純狀態 regression 先因 production 缺少新 policy 而 collection fail，修正後 `3 passed`；擴大
  G38-02 非 GUI 回歸 `176 passed`，版本／entrypoint／build source／stage-folder 精準回歸
  `28 passed`。CLI 實際輸出 `MediaManager 開發版 38.1.1`；Ruff／文字污染 `368 / 573`、
  MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall 與
  diff check 均通過。未執行 GUI 自動互動；UI 截圖與人工驗證不由自動化代替。

### 38.1.2｜緊湊 fallback 與明確作品／單集操作

- 38.1.1 截圖證明黑色 WebView 已隱藏，但大型深色對話框仍容易被辨識成全黑播放器；作品與
  單集操作也共用相同文字。
- presentation policy 現在同時決定 fail-closed 可見狀態與對話框 geometry：只有本機能力
  `SUPPORTED` 才使用大型內嵌區；其他狀態與 timeout／renderer failure 使用緊湊提示。
- 四語操作分別標示作品頁與選取單集，避免把作品 handoff 誤認為單集 handoff。本修正不增加
  codec、不讀取系統瀏覽器資料、不繞過 Cloudflare，也不攔截播放串流。
- geometry regression 先取得 production 缺少欄位的 collection RED；修正後精準非 GUI 回歸
  `18 passed`，擴大搜尋／集數／session／locale／版本文件回歸 `80 passed`。CLI 實際輸出
  `MediaManager 開發版 38.1.2`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall 與 diff check
  均通過。因此 38.1.2 記為 `SOURCE VALIDATED`；集數手動網址 fallback、選取單集 handoff 與
  官方正片播放仍為 `LIVE WAITING / NOT_RUN`，且本輪沒有自動操作 GUI 或連線官方網站。

### 38.1.3｜修復 AniGamer 內建完整性釘選

- Root Cause 是 38.1.2 新增四語作品／單集操作文字後，四個 locale 的 SHA-256 pins 未同步；
  安全完整性檢查因此正確拒絕 AniGamer parent，畫面顯示 `31/32` 與「初始化失敗」。
- 既有 pinned-integrity regression 先得到 `1 failed` RED；修正只更新 en、ja、zh-CN、zh-TW
  四個 digest，不關閉或放寬驗證。
- 完整性／bootstrap／搜尋／集數／session／locale／版本擴大回歸 `91 passed, 1 skipped`；全 built-in
  digest 掃描為零 mismatch，bootstrap verify-only 回到預期 `SAFE_MODE`，CLI 輸出
  `MediaManager 開發版 38.1.3`。Ruff、MOD、網站、依賴、版本與 compileall／diff Gate 均通過。
- 必須完全關閉舊 38.1.2 行程後啟動 38.1.3；面板「重新整理」只重畫既有 snapshot，不會重新
  載入啟動時被拒絕的 MOD。實際 `32/32`、集數與播放仍需使用者截圖，未由自動化宣稱完成。

### 38.1.4｜單集網址路由與目錄瀏覽器 fallback

- 工作區原本將 canonical `animeVideo.php?sn=...` 單集網址誤送到只接受作品的目錄 provider，
  因而顯示 catalog invalid；四個目錄快捷按鈕則共同受官方 Cloudflare browser-verification
  回應阻擋，並非四條 UI wiring 同時失效。
- 現在單集網址先經本機 strict classifier，只接受 exact host、canonical path、唯一 ASCII serial，
  並拒絕 userinfo、顯式 port、fragment、額外／重複 query、子網域與非 ASCII serial。通過後只建立
  獨立單集列，不推導作品或沿用舊作品；沒有正式作品時，作品歷史與離線保存保持停用。
- 目錄 provider 遇 browser verification 時只記錄目前 allowlist query；使用者再次明示點擊同一
  快捷操作才交給系統瀏覽器。錯誤 callback 不自動開啟外部程式，換按鈕、文字搜尋、取消、成功
  或其他錯誤都清除此狀態。此流程不讀取瀏覽器 Cookie、不繞過 Cloudflare，也不攔截播放串流。
- Regression 先得到缺少 classifier 的 ImportError RED；修正後精準 `4 passed`、擴大非 GUI
  `111 passed`。CLI 為 `MediaManager 開發版 38.1.4`；quality `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴 `10`、版本文件 `4`、保留版本 `5`、compileall 與 diff check 均通過。
  依截圖優先政策未執行會建立 QApplication 的 GUI test，也未連線官方網站。實際第二擊 handoff、
  完整集數與播放仍是 `LIVE WAITING / NOT_RUN`。
- 後續三張 38.1.4 截圖已證明：作品 `盜墓王` 可見兩筆集數列；canonical 單集 49853 可由本機
  分流為未綁作品的獨立單集；離線索引亦正確顯示尚未連結影片或字幕。截圖沒有顯示完整季集數
  來源、獨立單集列、OS handoff 或播放時間前進，因此不擴大為集數完整、播放或下載完成宣告。
- 38.1.4 已由 38.1.5 取代且未建立套件；上述來源與人工證據仍作歷史紀錄，不回寫判定。

### 38.1.5｜明確目錄交接與單集列可見性

- Root Cause 不是四個快捷按鈕 wiring 同時失效：38.1.4 截圖顯示第一擊已經完成
  browser-verification 分類與 arm。舊流程要求 async 完成後再次點擊「完全相同 raw query」的
  原按鈕，卻沒有顯示哪個操作已 armed 或提供獨立完成按鈕；busy 時快速連點會被忽略，換按鈕、
  搜尋、取消或其他狀態又會清除 arm。canonical 單集路由也已建立資料，但焦點只捲到單集區標題，
  實際表格仍在 fold 下，造成空白誤解。
- 38.1.5 在 browser-verification arm 後顯示獨立的官方目錄確認操作；只有使用者明示點擊它才把
  原始 exact allowlist query 交給 OS，錯誤 callback 仍禁止自動開啟。已有單集資料時，畫面焦點
  改移到 populated episode table；沒有資料時才退回標題。OS opener 失敗時保留確認操作，只有成功
  交接才清除 arm。這不匯入瀏覽器 Cookie、不繞過 Cloudflare、不自動控制 GUI，也不攔截或保存
  播放串流。
- 兩個主 regression 在修正前為 `2 failed`；OS opener 失敗後遺失確認操作的恢復性 regression 另為
  `1 failed`。完成修正後，含 no-auto-open、exact allowlist、四語、pinned integrity、版本、
  entrypoint、網站與依賴契約的擴充非 GUI 組為 `47 passed`。Ruff／文字污染 `368 / 573`、MOD
  `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、
  CLI 38.1.5 與 diff check 均通過；不宣稱 OS handoff、完整集數、播放或下載成功。
- Rollback 必須一起回復獨立確認操作、arm/action-state wiring、episode-table focus、四語文字、
  完整性釘選與 38.1.5 身分；不刪除使用者資料、不修改或覆寫 Development 38.0。
- 截圖證據界線：`codex-clipboard-9e44c01c-54e6-4259-a5d8-3b3ba545a594.png`（SHA-256
  `1c3720949e0530d404823f6047e91c6106782af603a39ffc11ca36dc0a5f8854`）與
  `codex-clipboard-24bbcaa7-fec7-41dc-a000-c69c88299252.png`（SHA-256
  `5605edd28f93048765b7890b286e1293bfc1790f3afef82e3e776e5a6e77f794`）只支持第一擊已 armed、但
  沒有獨立可見完成操作；不能證明點擊、網路結果或四鍵 wiring 斷線。
  `codex-clipboard-2d13c4cf-abe8-4afd-9169-6ee7b0b0468d.png`（SHA-256
  `0db2a37d53bf0b97d34c8bcf13baf7c2c480592b34a24ee8213abd3f43f276ae`）只支持 canonical 單集已
  本機辨識、上方結果表為空且畫面裁切在單集列之前；不能證明單集列不存在、完整集數、OS
  handoff、播放或下載。三圖保留為 38.1.5 pre-fix 證據，不取代既有 38.1.4 歷史截圖紀錄。

### 38.1.6｜Direct episode 可見性與官方目錄 handoff

- 38.1.5 最新畫面證明快捷操作與 canonical 單集搜尋均已進入 handler，故不是所有按鈕 wiring
  同時失效。實際缺口是 direct route 清空上方作品表後仍保留 220px minimum height 與三個無關
  作品動作，且焦點在填表前排程；單集 row 因而仍在 fold 下。另一個「相容性檢視作品頁」入口
  把官方目錄送進 media WebEngine codec gate，顯示與目錄用途無關的 H.264／AAC fallback。
- 38.1.6 在 direct route 收合空作品區與三個作品動作，正常作品搜尋填表時恢復；單集填入並選取後
  再排程定位。目錄入口改成使用者明示點擊的 system-browser allowlist handoff；存在 armed query
  時沿用該 exact target，成功才清除，OS opener 失敗時保留重試，未 armed 時才使用一般官方目錄。
  不自動開啟瀏覽器、不匯入 browser profile／Cookie、不繞過 Cloudflare／登入／廣告／DRM，亦不
  攔截或保存播放串流。
- RED 依序為 direct visibility／post-focus `2 failed`，catalog media-routing、成功 state cleanup、
  armed exact-target 與重複同名操作各一個獨立 `1 failed`；完成最小修正後六項純 AST／邏輯
  regression 為 `6 passed`，擴充非 GUI 組為 `105 passed`。Ruff／文字污染 `368 / 573`、MOD
  `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、
  CLI 38.1.6 與 diff check 均通過。實際 widget 幾何、四個快捷點擊與 OS handoff 仍需
  screenshot-first 人工驗證。
- Rollback 逐項回復 result-area visibility、post-populate focus、catalog handoff／exact armed target
  與 38.1.6 身分；不刪除使用者資料、不修改或覆寫 Development 38.0。
- 截圖證據：`fa442f06…`（SHA-256
  `ECBC583EB97BAA2A8774C02627847BCB01113FEC589AE9F6931B545E1FC54CE3`）只證明 arm 與明示操作
  可見；`552848cc…`（SHA-256
  `71FEEF01E3CE71D616755581E94CCE124B04AFF3982B321173B696A068AB5CBE`）證明另一條目錄路徑誤入
  codec fallback；`ea3bfea7…`（SHA-256
  `CECCEF2F01CE18F4282703BB61A8E426E6C8C438500DC0F4EBEAB7902B52CFEC`）證明 canonical 單集已
  本機辨識但 row 未進入 viewport。三圖都不證明點擊、OS handoff、完整集數、播放或下載成功。

### 38.1.7｜手動集數無損附加與 fallback Retry

- 38.1.6 人工畫面顯示介面篩選後按「重試」可重新取得 20 筆官方作品；20 是目錄 provider 的
  單一來源安全上限，不是 stale 結果。產品缺口位於集數驗證 fallback：每次加入 canonical 官方
  單集網址都取代既有清單；系統瀏覽器官方頁可見四集時，工作區仍只保留最後一列。
- 38.1.7 將手動集數改為 lossless append，使用 `video_id` 與 canonical URL 去重，並在集數
  browser-verification fallback 內新增呼叫相同操作的「重試」。不推算相鄰 SN、不讀 browser
  DOM／Cookie、不從頁面抽取集數、不繞過 Cloudflare／登入／年齡／廣告／DRM。
- 新 helper 實作前以 import／collection `1 error` 取得 RED；最小修正初次兩項精準回歸為
  `2 passed in 0.89s`，加入 fallback wiring 後為 `3 passed in 0.97s`。review 再以 `2 failed`／
  `1 failed` 關閉 append failure 游標、malformed URL 與同系列分頁游標缺口；最終精準組
  `6 passed in 1.10s`，擴大非 UI 組 `111 passed in 1.85s`。Ruff／文字污染 `368 / 573`、MOD
  `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall、CLI
  38.1.7、Version bytecode 零污染與 diff check 均通過，來源標記 `SOURCE VALIDATED`。
- 終端可見的 Video.js `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED` 與 `setVolume` TypeError 分類為
  本機 codec／站方播放器次生錯誤。系統瀏覽器仍是播放主路徑；本修正未安裝 codec、未改站方
  腳本，也未把內嵌播放宣稱為成功。
- 八張 38.1.6 post-fix／38.1.7 pre-fix 截圖及完整 SHA-256 保存於 canonical roadmap；它們支持
  20 筆重新查詢、安全上限、手動集數覆寫與官方四集對照，但不證明完整集數、播放或下載完成。
- 後續四張 38.1.7 post-fix 截圖確認可見版本、fallback Retry 入口與 `sn=49945` 單一集數列；
  `version_visible`、`episode_retry_visible`、`manual_single_add` 記為 `PASS`。因未同時顯示第二個
  不同集數與重貼結果，append／dedupe 尚未執行；Retry trigger、episode OS handoff 與 system-browser
  播放亦為 `NOT_RUN`。完整 SHA-256 保存於 canonical roadmap；純證據更新不升版或建立套件。
- Rollback 為一起回復 merge helper、手動加入／fallback Retry wiring 與 38.1.7 身分；不刪除
  使用者資料、不修改或覆寫 Development 38.0。

### 38.1.8｜搜尋失敗保留上一批有效狀態

- 兩張 38.1.7 人工畫面顯示輸入關鍵字後已進入瀏覽器驗證狀態，搜尋／重試仍啟用，但作品表
  變空。來源追蹤確認官方 403 被 federation 包成 `FederatedSearchResult.failures`；舊工作區在
  檢查 failure 前先提交空 results、清除作品選取與集數，而直接 exception 路徑不會清除，形成
  可重現的不一致回退。
- 38.1.8 加入純 result reducer：只有 `failure + 0 accepted item` 保留上一批有效作品、選取與
  集數；partial success 仍提交有效 item，真正成功的空結果仍清空。四語訊息明示保留列不是
  本次查詢結果，避免把 stale 資料誤認為新結果。首次受阻且沒有上一批資料時仍為空表，並要求
  使用系統瀏覽器取得 canonical `animeRef.php`；不讀 browser profile／Cookie、不自動開 GUI、
  不繞過驗證。
- 新 reducer 尚不存在時先以 import／collection `1 error` 取得 RED；實作與 wiring 後精準非 UI
  組 `2 passed in 0.43s`；最終 review 補上非瀏覽器 structured failure 的通用保留提示後，提示／
  四語／integrity 精準組 `5 passed in 0.45s`，擴大搜尋、集數、session、MOD integrity、bootstrap、
  版本與文件組為 `103 passed, 1 skipped in 3.20s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall、CLI 38.1.8、Version
  bytecode 零污染與 diff check 均通過。未執行 GUI 自動互動或官方網路請求，故來源為
  `SOURCE VALIDATED / LIVE WAITING / SAFE_MODE`。
- Pre-fix 截圖 SHA-256：`9d48…` 為
  `3439213CD04B897A60BBFB7F52DDB6F3AE71712EC49C29C2CC26F192422DE78C`；`d97a…` 為
  `FFBEEAEF9ABE58524F26AF6C2E5BB11037D34A2051489F09D01C47F4532BEB32`。兩圖不證明 403 的
  供應者或網路內容，只固定可見症狀。
- 2026-07-22 post-fix 截圖顯示 38.1.8 的三筆作品、`盜墓王` 選取 context 與兩筆集數列可見，
  另顯示相容性檢視在本機 Qt codec／HLS／MSE 不支援時正確隱藏 WebView 並提供系統瀏覽器主操作。
  這只使 `catalog_results_visible`、`series_selection_visible`、`episode_rows_visible` 與
  `embedded_fail_closed_presentation` 成為人工 `PASS`；OS handoff、系統瀏覽器正片播放、
  38.1.8 failure-state preservation 與下載仍為 `NOT_RUN`。完整檔名與 SHA-256 保存於 canonical
  roadmap；純證據更新不升版。
- 同日驗證發現 workspace GUI 測試仍綁定舊的 `Cloudflare` 搜尋字樣與舊的通用相容性按鈕標籤；
  兩處只改為比對目前 locale key，不改 production code、不升版。後續非 UI AniGamer／MOD 精準組
  為 `90 passed in 1.03s`，品質、MOD、網站、依賴、版本、compileall 與 diff checks 均通過；依
  screenshot-first 界線沒有重跑自動 GUI，故完整 GUI suite 明確維持未驗證。
- 同日重新檢查動畫瘋官方服務條款與官方 App 說明：官方只提供依其服務方式線上觀看，沒有
  可供第三方保存的公開影片匯出契約，且條款禁止重製、規避廣告與破解串流。因此合法離線影片
  保持 `BLOCKED / NO AUTHORIZED MEDIA SOURCE`；不把瀏覽器、WebEngine、service worker 或播放器
  暫存轉作下載，也不以 Cookie 或網頁可播放推論下載授權。
- Rollback 為一起回復 reducer、`show_search_results()` wiring、四語提示／integrity pins 與
  38.1.8 身分；不刪除使用者資料、不修改 Development 38.0。尚未 stage、commit、freeze、build
  或建立候選包。

### 38.1.9｜切換作品時丟棄舊集數回應

- **Symptom／Trigger**：作品 A 的非同步集數請求尚未完成時切換到作品 B，selection handler 只
  清除集數狀態，沒有使該 worker 的 generation 失效。A 回應抵達後仍能進入共用
  `show_response()`，把 A 的成功結果或失敗提示套到 B；後續播放歷史與離線索引可能把 A 集數
  和目前 B 作品配對。
- **Root Cause／Fix**：舊 dispatch 只比對 operation generation，未比對 episode request 的作品
  ownership。38.1.9 新增純 guard；只有 `episode_query` 仍為非空字串且完全等於目前選取作品 URL
  時，才呼叫 `show_episode_results(response, error)`。不一致時丟棄舊成功與失敗回應並結束 busy，
  不改目前作品的集數、游標、fallback 或狀態。
- **Compatibility／Risk**：provider protocol、目錄與集數 URL、Cookie、網路、codec、系統瀏覽器
  handoff、UserData 與 Development 38.0 都不變。唯一行為差異是 stale response 不再可見；同一
  作品正常回應仍接受。風險低，且沒有新的 UI 文字、manifest 或 integrity pin。
- **Validation**：helper 與 dispatch guard 尚不存在時兩個純測試先得到 `2 failed in 1.25s`；最小
  修正後同組 `2 passed in 0.24s`；本輪 AniGamer 搜尋、集數、session、純 workspace 與版本組合計
  `85 passed in 1.77s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、Repository 外 pycache compileall、CLI 38.1.9 與
  `git diff --check` 均通過。未啟動或控制 GUI、未連線官方網站；人工競態與播放仍為
  `LIVE WAITING`。
- **Rollback**：一起回復 ownership helper、episode dispatch guard、兩項 regression 與 38.1.9
  來源身分；不刪除使用者資料、不修改 provider 或覆寫 Development 38.0。尚未 stage、commit、
  freeze、build 或建立候選包。

### 38.1.10｜收斂動畫瘋 canonical query 邊界

- **Symptom／Trigger**：動畫瘋作品或單集網址雖位於 exact host 與 canonical path，舊 routing 仍會
  接受 `sn` 以外的額外參數、重複 `sn`，或經大小寫／percent encoding 形成的 alias；這些網址可
  穿過共用分類後進入 provider 過濾、系統瀏覽器 handoff、history 或 offline 邊界。
- **Root Cause／Fix**：舊判定只解析 query 值並檢查數字，沒有要求原始 query bytes 的 canonical
  形式。38.1.10 在共用 AniGamer route 只接受原始 query 精確等於 `sn=<ASCII digits>`；額外、重複、
  `SN=`、percent-encoded key／value 或其他 alias 一律 fail closed。四個 consumer 因共用 classifier
  同時取得相同保護，不新增 provider／網路行為。
- **Compatibility／Risk**：標準 `animeRef.php?sn=123` 與 `animeVideo.php?sn=456` 行為不變；非精確
  alias 現在拒絕。風險低，沒有資料格式、UserData、Cookie、manifest、codec、UI 或資料遷移變更。
- **Validation**：額外／重複 query regression 先為 `1 failed in 0.46s`；擴充大小寫與
  percent-encoded alias 後第二階段為 `1 failed in 0.41s`；精確 route node 最小修正後為
  `1 passed in 0.17s`。相關非 UI 組 `205 passed, 1 skipped in 1.66s`，版本／文件組
  `19 passed in 1.00s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、Repository 外 pycache compileall、CLI 38.1.10、Version
  bytecode 零污染與 diff check 均通過。未啟動或控制 GUI、未連線官方網站，也不宣稱 OS handoff、
  播放或下載完成。
- **Rollback**：只回復 `core/site_routing.py` 的精確 query 條件、相符 regressions、38.1.10 版本與
  文件；不刪除或遷移資料、不修改 provider，也不覆寫 Development 38.0。尚未 stage、commit、
  freeze、build 或建立候選包。

### 38.1.11｜鎖定 canonical item identity 與單集 handoff 狀態

- **Symptom／Trigger**：canonical AniGamer `DiscoveryItemV1` 即使 `video_id` 與精確 URL 的 `sn`
  不一致，仍可進入 provider results、handoff、history 或 offline；另外，busy 期間雙擊仍留在畫面上的
  舊單集列可觸發 handoff。
- **Root Cause／Fix**：consumer 原先只驗 URL route，沒有共用 ID／URL identity invariant；單集
  double-click handler 也沒有 busy／closing guard。38.1.11 新增共用純 validator，要求作品 ID
  精確為 `ani-{sn}`、單集 ID 精確為 `ani-episode-{sn}`，並套用至作品／集數 filter、series／episode
  handoff、history 寫入及讀取與 offline 寫入及 metadata 讀取；episode handoff 在 busy／closing 時
  fail closed。
- **Compatibility／Risk**：內建 provider 原本已產生 canonical IDs，current-series 與 direct-episode
  context 保持原語意。沒有 schema、network、Cookie、codec 或 download capability 變更，也沒有
  migration／deletion；既有檔案保持不動。
- **Validation**：validator／consumer wiring／handoff guard 尚未存在時，精準回歸先為
  `4 failed in 1.80s`；最小修正後初始精準組為 `6 passed in 1.26s`。read-side review 再以
  `2 failed in 0.52s` 重現 history load 與 offline metadata 讀取缺口，修正後為
  `3 passed in 0.98s`；最終相關非 GUI 組為 `129 passed, 1 skipped in 7.23s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 compileall、CLI 38.1.11、Version bytecode 零污染與 diff check 均通過。沒有啟動或
  控制 GUI，system-browser 播放仍為人工 `LIVE WAITING`，內嵌 codec 不支援仍是預期限制。
- **Rollback**：一起回復 identity validator、consumer wiring、history／offline read-side checks、
  busy／closing guards、regressions、
  38.1.11 版本與文件；不刪除或遷移資料、不修改既有檔案或覆寫 Development 38.0。尚未 stage、
  commit、freeze、build 或建立候選包。
- **Live screenshot evidence（evidence-only）**：`codex-clipboard-9b3bf123-feeb-4f9c-95e9-13b1ec70f0ea.png`
  （SHA-256 `81733D7FC2DAB30DC5ED1CB257235AAFDB5E39F13DA764F5937AD6BF2B571990`）顯示
  38.1.11 的 compact fail-closed 提示，終端同時記錄 Video.js `CODE:4` 與 `setVolume` TypeError；
  `codex-clipboard-92c95b19-5fca-4c05-bf57-2054ba5e62ab.png`（SHA-256
  `E46E4C90AFBBC5028E138FDBF3AE42C89BB1201969135A07BDA841D2431CD986`）顯示版本 38.1.11、
  `盜墓王 [1]`／`[2]`、選取第 2 集、單集 system-browser／compatibility 操作及 offline metadata
  index 有效但未連結影片或字幕。這些只使可見版本、兩筆集數、選取單集、操作、fail-closed
  presentation 與 metadata index 為 `PASS`；內嵌播放為 `EXPECTED_UNSUPPORTED`，system-browser
  handoff／播放、完整總集數、下載及檔案完整性仍為 `NOT_RUN / LIVE WAITING`。該訊息也未顯示
  exact URL，所以無法把 OS handoff 與選取的 canonical episode URL 對應；這些 38.1.11 畫面
  不得當作 38.1.12 live evidence。

### 38.1.12｜在單集 OS handoff 訊息保留 exact URL

- **Goal／Priority**：P1 是讓人工驗證可把 MediaManager 報告的 OS 開啟請求對回選取單集的
  exact canonical URL；它只強化證據可追蹤性，不將 OS 接受請求誤報為頁面載入或播放成功。
- **Scope／Approach**：四語 `episode_opened` 資源加入 `{url}`；`open_selected_episode` 與
  `open_history_entry` 使用實際交給 OS 的 exact URL 格式化訊息。文案明示 OS 已接受
  請求，但官方頁載入與播放仍未確認。不改 Cookie、provider traffic、串流、codec 或下載。
- **Compatibility／Risk**：依賴 38.1.11 的 canonical item identity 與現有 allowlisted OS opener；只改內建四語
  placeholder 與呼叫點，沒有 schema、IPC、資料或網路相容性變更。主要風險是「OS 已接受」被誤解為
  「已播放」，因此文案必須同時保留未確認頁面載入／播放的限制。
- **Validation**：修正前回歸為 `1 failed in 0.42s`；修正後為 `2 passed in 0.94s`，精準相關來源組
  `9 passed in 1.04s`，擴大非 UI 回歸組 `143 passed, 2 skipped in 1.60s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  版本文件測試 `6 passed in 0.33s`、Repository 外 compileall、CLI 38.1.12、Version `.pyc`
  零污染與 diff check 均通過。未啟動或控制 GUI，未取得 38.1.12 system-browser 頁面載入／播放證據。
- **Rollback／Release boundary**：一起回復四語文案，`{url}` wiring、regressions、38.1.12 版本與文件。
  沒有 migration／deletion，不覆寫 Development 38.0。尚未 stage、commit、source freeze、build、package 或 push。

### 38.1.13｜讓相容性彈窗顯示 exact-route handoff 結果

- **Goal**：P1 修正相容性彈窗在使用者仍看著 modal dialog 時無法得知 OS handoff 實際結果的
  可觀察性缺口，並避免單集或作品 URL 被誤標成「官方目錄」開啟成功。
- **Scope**：只調整相容性彈窗的 route-aware handoff 訊息、dialog-local status 鏡像、相符
  regression、版本與文件。不改 provider、network、Cookie、download、stream、codec、schema、
  IPC、離線格式或站點存取政策。
- **Priority**：P1；相容性檢視是現行內嵌 codec fail-closed 後可見的交接入口，錯誤的訊息類型或
  被彈窗遮住的失敗狀態會直接妨礙人工判斷是否已把正確官方 URL 交給 OS。
- **Dependencies**：沿用 38.1.10 exact route、38.1.11 canonical item identity、38.1.12 的
  `episode_opened` exact URL 文案與既有 allowlisted OS opener；G39／G40 不平行啟動。
- **Approach**：相容性彈窗不再固定呼叫 `catalog_opened`。它先分類 exact AniGamer route：單集使用
  `episode_opened` 並帶入實際送交 OS 的 exact URL，作品使用 `series_opened`；OS 接受、拒絕或
  opener 拋出 `RuntimeError` 的最終文字，同步寫入工作區主狀態與彈窗內 local status。
- **Compatibility**：系統瀏覽器仍接收同一 allowlisted 官方 URL，按鈕、provider contract、Cookie
  lifetime、資料與網路行為不變；沒有 migration 或 breaking change。
- **Risk**：主要風險是 route／placeholder 選錯、成功被誤報，或只更新其中一個狀態而讓 modal
  仍遮住結果。exact-route regression 與 dialog-local 鏡像 assertion 為對應控制；人工截圖尚待。
- **Rollback**：一起回復 exact-route 訊息選擇、dialog-local status 鏡像、regression、38.1.13
  版本與文件。不刪除或遷移資料，不覆寫 Development 38.0，也不改 provider、network、Cookie、
  download 或 stream。
- **Validation／Release boundary**：修正前精準 regression 為 `1 failed in 1.27s`；最小修正後為
  `1 passed in 0.71s`；相關精準組 `3 passed in 1.28s`、擴大非 GUI 組
  `115 passed, 1 skipped in 3.77s`、版本／文件組 `19 passed in 1.21s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 compileall、CLI 38.1.13、Version `.pyc` 零污染與 diff check 均已完成；目前為
  `SOURCE VALIDATED`。人工
  38.1.13 截圖仍為 `LIVE WAITING`，不得以來源測試宣稱 OS handoff、頁面載入或播放完成。未
  stage、commit、source freeze、build、package 或 push。

### 38.1.14｜分離官方 handoff target 與訊息 URL placeholder

- **Goal**：P1 修正單集官方 handoff 在呼叫 helper 時即因 Python 參數綁定衝突失敗，讓
  38.1.12／38.1.13 的 exact URL receipt 與 dialog-local 結果能真正進入 helper 執行。
- **Scope**：只將 `dispatch_official_url` 的 transport positional 參數由 `url` 改名為
  `official_url`、同步其內部 opener／失敗訊息引用，並加入精準 regression、版本與文件。不改
  provider、network、Cookie、download、stream、codec、schema、IPC、離線格式或站點存取政策。
- **Priority**：P1；選取單集、history 與相容性彈窗單集 fallback 都會同時傳入 positional target
  與 `url=` message placeholder，衝突會在 helper body、OS opener 與 local status 更新前發生。
- **Dependencies**：沿用 38.1.12 `episode_opened` exact URL placeholder、38.1.13 route-aware
  dialog-local status、canonical identity 與 allowlisted OS opener；G39／G40 不平行啟動。
- **Approach**：保留呼叫端的 positional target 與 keyword `url=` 文案資料；只把 helper 的 transport
  formal parameter 改為 `official_url`，並讓 opener 與 `system_browser_open_failed` 使用該名稱，
  避免 `**values` 中的 `url` 與 formal parameter 再次碰撞。
- **Compatibility**：呼叫順序、allowlisted URL、翻譯 placeholder、成功／失敗文案與
  dialog-local 鏡像語意不變；沒有 migration 或 breaking external API。
- **Risk**：主要風險是內部引用漏改、失敗文案取錯 URL，或只以 AST 形狀測試而未覆蓋實際
  argument binding；精準 signature／opener／failure-message regression 與 handoff 組為對應控制。
- **Rollback**：一起回復 helper 參數名稱與內部引用、regression、38.1.14 版本與文件。不刪除或
  遷移資料，不覆寫 Development 38.0，也不改 provider、network、Cookie、download 或 stream。
- **Validation／Release boundary**：runtime 擴大組修正前為
  `1 failed, 162 passed, 1 skipped in 8.99s`；新增純回歸 RED `1 failed in 1.20s`；修正後純 handoff
  組 GREEN `4 passed in 1.08s`。後續相關非 UI＋版本組在文件尚未同步時為
  `134 passed, 1 skipped, 1 failed in 6.79s`，唯一失敗只因 README／docs README 仍為 38.1.13；
  文件同步後重跑為 `135 passed, 1 skipped in 1.87s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、
  網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、
  CLI 38.1.14、Version `.pyc` 零污染與 diff check 均已通過，故該輪為 `SOURCE VALIDATED`。人工 38.1.14 截圖當時維持
  `LIVE WAITING`；不得以來源測試宣稱 OS handoff、頁面載入或播放完成。未 stage、commit、
  source freeze、build、package 或 push。
- **Evidence-only screenshot**：`codex-clipboard-5687e504-c306-4d3a-86b0-cc79cf9d8567.png`
  （SHA-256 `5C52283BACEB1EECB5E55F92A1301D1E6240239D0F2BD6CDA1C1BEEB05DE5E42`）可見從
  `C:\Dev\MediaManager` 執行 `.\.venv\Scripts\python.exe .\main.py`、標題「盜墓王 [1]」的緊湊
  相容性 fallback、Qt WebEngine 缺本機 H.264／AAC／HLS／MSE 路徑提示、system-browser 建議操作與
  取消按鈕；終端同時可見 Video.js `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED` 與 `setVolume` TypeError。
  CLI 另核對當時來源 38.1.14。判定只包含 `embedded_fail_closed_presentation=PASS`、
  `episode_context_visible=PASS`、`system_browser_action_visible=PASS` 與
  `embedded_playback=EXPECTED_UNSUPPORTED`；畫面沒有證明按鈕已點、OS handoff、官方頁載入、廣告或
  播放，因此維持 `LIVE WAITING / SAFE_MODE`，本次純證據同步不升版。
- **Reference-only fork audit**：BoringMan314/aniGamerPlus V24.9.10（`ce7a6d5`）採 GPL-3.0；
  未把其程式碼複製進 MIT tree。可接受的通用功能已由既有命名、queue、retry、concurrency、
  log rotation、history 與 offline integrity 吸收；遠端服務與本機 MP4 `faststart` 跨 Gate 延後；
  Cookie／Cloudflare／代理／串流分段／金鑰／解密與廣告規避排除。沒有新的 G38 material delta，
  故標記 `ABSORBED / NO RELEASE`，該輪維持 38.1.14 且沒有建立下一修正號；後續 38.1.15
  是獨立的移除差異。相關非 UI／版本／文件組以
  唯一 LOCALAPPDATA test-root 重跑為 `173 passed, 1 skipped in 5.36s`；quality、MOD、網站、依賴、
  版本、Repository 外 compileall 與 diff Gate 均通過。

### 38.1.15｜移除動畫瘋 MOD 與目前來源註冊

- **Decision／Status**：使用者決定停止動畫瘋整合並專注其他功能。G38-02 因而標記
  `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`；38.1.14 為
  `SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`，38.1.15 為
  `SOURCE VALIDATED / ANI-GAMER MOD REMOVED / NO PACKAGE / SAFE_MODE`。
- **Scope**：從目前來源移除動畫瘋父 MOD、目錄搜尋、集數導覽、相容性播放器、session Cookie、
  離線索引 UI、site route、bootstrap／self-check／integrity 註冊與專屬測試；不修改不可變
  `Version/Development/38.0`，也不建立套件。
- **Compatibility／Migration**：不刪除或覆寫既有 UserData、歷史、離線索引、封面或使用者自行
  選取的本機媒體。舊設定中的 `ani-gamer*` 只作已退役未知 ID，不能使啟動失敗，也不會重新註冊。
- **Security boundary**：不得把退役動畫瘋網址接到 Direct HTTP、yt-dlp、ffmpeg 或其他 generic
  adapter；Cookie／profile、Cloudflare、登入、DRM、付費、地區、廣告與播放串流限制不繞過。
- **Risk／Rollback**：風險是殘留 catalog、tab、bootstrap、route 或 integrity pin 造成幽靈入口，
  或錯刪使用者資料。以 production-tree 零註冊與舊設定兼容 regression 控制；Rollback 只整體回復
  38.1.14 source／tests／documents，不覆寫歷史成品或使用者資料。
- **Release boundary**：本段只同步來源身分與發行紀錄；stage、commit、source freeze、build、EXE、
  Testing／Stable、簽署、發布與 push 均未執行。
- **Validation（2026-07-22）**：完整 repository runner `1201 passed, 6 skipped in 78.10s`；
  修正 stale built-in count 的精準回歸 `3 passed`。quality audit 為 Ruff `355`／文字 `549`；
  MOD 群組 `7 groups / 4 locales`、網站矩陣 `12 sites / 33 features / 49 workflows`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、來源 `.pyc` 零污染與 runtime
  零動畫瘋註冊均通過。live provider smoke 因缺少 bundled Deno／FFmpeg 為
  `WAITING / 0 passed, 7 failed`；未進行網站成功宣稱，維持 `SAFE_MODE`。

### 38.1.16｜封裝來源精確白名單

- **Root Cause**：`MediaManager.spec` 原以整個 `mod/builtin` 目錄作為 PyInstaller data input；
  PyInstaller 會遞迴展開 ignored `.pyc` 與工具 cache，而 source fingerprint 與 Git clean
  無法證明這些本機殘留未進入 EXE。
- **Scope**：依 `PINNED_BUILTIN_RELEASE_FILES` 逐檔建立 data inputs，缺檔、symlink 或來源根目錄
  escape 一律 fail closed。不刪除工作樹 cache、不修改不可覆寫 Development 38.0，也不變更
  runtime provider 或使用者資料。
- **Compatibility／Risk**：只改新候選的封裝輸入列舉；清冊內 87 個檔案維持不變。風險是未釘選
  的合法檔案被拒絕，新增內建 MOD 檔案時必須先同步 integrity inventory，不能靠遞迴目錄暗中帶入。
- **Rollback**：完整回復 helper、spec contract、回歸與 38.1.16 身分；回退到遞迴收集會重新開啟
  本機殘留污染風險，因此只能作 source revert，不能宣稱安全候選。
- **Validation**：回歸先以 helper 不存在與 broad directory tuple 重現 `3 failed`；修正後
  `tests/test_stage_version.py` 全檔與 spec contract 為 `12 passed`。使用相同 PyInstaller 6.21
  純展開得到 `87 pinned / 87 expanded / 0 unexpected / 0 missing / 0 contaminating`；
  `git diff --check` 通過。尚未取得 build 授權，post-build EXE 內容仍為 `WAITING`。

### G39-01｜固定 workload measurement baseline

- **Status**：`MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`；此為量測證據，不建立 39.0 版本或附件。
- **Source identity**：量測當下（後續只同步 evidence 文件）為 38.1.15，fingerprint
  `c86b4a75eb5210a56b56b3730ef179ec83835e1ffe128987a4000be5d020e6bf`，revision
  `3a35ab2b7c200f29920e3b25d9d0d7a8d4f7f014`。
- **Command／Workload**：`.\.venv\Scripts\python.exe -m tools.g39_baseline --warmups 2 --iterations 20`；
  `queue-roundtrip-v1` 固定 1,001 tasks／4 workers。
- **Results**：persist p50／p95／max `198.654 / 219.921 / 229.945 ms`；restore
  `212.36 / 240.687 / 260.336 ms`；worker `1.075 / 1.402 / 1.733 ms`；total
  `437.495 / 482.475 / 506.929 ms`。tracemalloc peak
  `20,145,600 / 20,146,368 / 20,146,560 bytes`，temp peak 每輪 `912,806 bytes`；process
  handle／thread delta 最大皆 `0`，殘留 download threads `0`，cleanup `true`。
- **Validation／Decision**：擴充 G39／queue regression `47 passed`、post-G39 完整 repository runner
  `1212 passed, 6 skipped`，quality audit Ruff `357`／文字 `551`；固定 workload 未顯示資源洩漏
  或足以啟動最佳化的 material bottleneck，因此不修改 runtime 行為、不升版本、不建立 release。
  G38-01 人工矩陣、38.1.15 live runtime blocker、G40 staged verify／headless SAFE_MODE 證據與正式簽署限制均原樣保留。
