# Development 37.0–38.0 更新紀錄

狀態：Development 37.0 source-only Exit Gate 已完成，判定為 `EVIDENCE READY / NO CLAIM`；目前核心
相容版本已同步為 `38.0.0`。使用者已明確授權將目前 35.0～38.0 核准變更 stage、本機 commit 並固定為
Development 38.0 source freeze，再建立一次 Development 38.0 SAFE_MODE 未簽署候選包；該包已由
實際 post-build 稽核通過。本文不是 Testing／Stable 宣告、正式簽署證據或原生 crash 已修復聲明。

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

現為唯一 `ACTIVE / G38-01 P1 FIXES VALIDATED / MANUAL REVALIDATION BLOCKED / SAFE_MODE`。
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
