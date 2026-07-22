# MediaManager 正式版 1.0 候選狀態

狀態：`ready: false / G39-09 SOURCE VALIDATED / SOURCE FREEZE WAITING / BUILD BLOCKED / NO STABLE PACKAGE / SAFE_MODE`。

本文件只記錄目前候選評估，不是 Stable 發布宣告。正式版使用獨立公開版本 `1.0.0`，目前
開發來源相容版本為 `39.0.7`；數字大小不可跨 Development／Testing／Stable 通道比較。

## 目前可確認的來源基線

- G39-06／Development 39.0.4 已修正 Gopeed／P2P 有限高度下 card 被壓扁重疊的版面缺口；
  來源使用既有 `workspaceScroll` 與 minimum-size layout contract。G39-07／39.0.5 再將 Stable
  公開身分與 UI display 固定為 `1.0.0`／「正式版 1.0」，並完成 receipt-bound
  build-only／stage-built 來源 operator。
- G39-08／39.0.6 新增 dry-run-first 本機歷史整理計畫；這是 Stable 已驗證且已上傳後的
  後置清理邊界，不是 Stable 建立步驟，目前沒有刪除任何檔案。
- G39-09／39.0.7 已把 production Ed25519 的非秘密 key ID／public key 編入來源，並新增
  32-byte raw public key 回歸。私鑰保存在 Repository 外；這不代表候選已簽署。
- 目前 catalog 有 29 個內建 MOD；新 profile 只有 `speech-to-text` 與 `automation` 預設停用。
  MOD 群組稽核為 7 groups／4 locales；網站矩陣為 12 sites／33 features／49 workflows。
- 39.0.7 的 116 個不含 PySide／GUI 操作測試檔合計 `1030 passed, 6 skipped`；
  release／version 精準回歸 `27 passed`；
  Ruff／品質、依賴鎖、
  版本文件、保留版本、Repository 外 compileall、SAFE_MODE verify-only 與 diff check 均通過。
- 修正版 UI 尚待使用者截圖確認；截圖不能取代 Tab／Shift+Tab、UIA／讀屏、Windows OS
  高對比或實際 Gopeed 互動證據。
- 最新保留完整包仍是 `Version/Development/38.0`。它屬不可覆寫的舊 source freeze，不能冒充
  39.0.7 或 Stable 1.0。

## 實測的 Stable 阻擋

對 `Version/Development/38.0` 執行唯讀 `tools.release_preflight --json` 得到 `ready: false`：

1. production Ed25519 公開身分已編入 39.0.7 來源，但這個 material delta 尚未 stage、commit 或
   source freeze；因此不能用 39.0.6 revision 建立候選。
2. `MediaManager.exe` 的 Authenticode 狀態仍為 `NotSigned`，且尚未取得 production
   Authenticode 身分或工具。
3. 舊包缺少 `gopeed-transfer`、`p2p-transfer`，且格式工廠／Local Ad Segment Trim manifest
   與目前來源 hash 不同；因此它不是目前候選。
4. Development 39.0.5 與 39.0.6 的 stage、本機 commit 與 source freeze 已於 2026-07-23 完成；
   兩者保持不可變，但 39.0.7 固定前都不可當成目前 build 來源。
5. split-phase operator 雖已通過來源／模擬失敗回歸，但尚未取得 production Authenticode 身分，
   也沒有對真實 build-only EXE 得到 `Valid`；receipt 不能替代正式簽章。
6. 尚未建立綁定同一 revision、EXE digest、runtime、SBOM、checksum 與工具版本的新 Testing
   候選，也未完成 copied-folder current→previous→current、headless SAFE_MODE 與上傳前後 digest。

不得以 Development 38.0、既有 Testing 1.0／1.1、測試金鑰、手動改狀態或移除 preflight
檢查替代上述證據。

## 歷史與清理政策

- `README.md` 已只保留目前 Development 39.0.7、Stable 1.0 候選、最新能力、安全界線與操作入口；
  舊版細節改由 `docs/README.md` 的唯讀索引與區間 release／roadmap 文件承接。這是資訊收斂，
  不是刪除公開歷史或供應鏈證據。
- GitHub Releases 上已公開的 EXE、`SHA256SUMS.txt`、`release-info.json`、tag 與附件不可刪除或
  覆寫；保留版本目錄的 checksum 證據亦不得改寫。
- `Version` 與 `UserData` 被 `.gitignore` 忽略，但分別包含不可變成品與使用者資料；禁止使用
  `git clean -fdX` 或 broad wildcard 清理。
- 可另行清理的只有已確認無程序持有、無 rollback／稽核價值的 cache、pytest temp 與 build
  residue；每個根目錄須先確認絕對路徑並採白名單刪除。
- `tools.prune_local_history` 只是預設 dry-run 的本機 `Version` 計畫器；未保留兩版、沒有
  publish-ready Stable、候選含 UserData／link-like 內容，或沒有 exact confirmation 都會拒絕。
  實際刪除只能在 Stable 上傳後 digest 驗證與獨立授權完成後執行。
- `Version/Development/16.1/UserData` 的 6 個檔案中有一份舊 audit 與目前 UserData 不同；它
  不是可丟棄的重複內容。清理前須先保存到 `Version` 外、逐檔驗 hash，且不得覆寫目前 audit。
- 對使用者只需在 README、目前 release note 與本文件呈現最新更新資訊；歷史工程文件可以
  標為 Historical／Deprecated 或移至封存索引，但不以刪除公開證據換取介面整潔。

## 重新評估與正式發布順序

1. 完成 39.0.7 的來源 Gate；人工 UI 證據維持截圖優先。
2. 另行取得 stage、本機 commit 與 39.0.7 source-freeze 授權並固定精確 clean revision；
   commit hash 與 tree fingerprint 由交付回報保存，避免自我參照。
3. production Ed25519 public identity 與 Repository 外私鑰已建立；仍須取得 Windows
   Authenticode 身分。私鑰不得寫入 Repository、參數紀錄、Log 或套件。
4. 另行取得 build 授權後，以 `--channel stable --confirm-stable --build-only` 建立 receipt-bound
   handoff；外部套用並驗證 Authenticode `Valid` 後，另行取得 stage-built 授權再執行
   `--channel stable --confirm-stable --stage-built <work>`。不得沿用單步 Stable build-and-stage。
5. 在 stage 後產生 SHA-256／SBOM，使用 production Ed25519 簽署最終 exact set；任何簽署後修改
   都使候選失效。
6. 執行完整版本稽核、copied-folder、headless、候選 evidence 與上傳前 digest；
   `tools.release_preflight` 必須回傳 `READY`。
7. 再取得 Stable 建立、發布與上傳目的地的明確授權，建立新的 Stable 1.0 Release；不得覆寫
   既有版本或先刪除歷史附件。

只要任一 production 身分、人工證據、source freeze 或候選 digest 缺少，就維持
`SAFE_MODE / ready:false`，不得建立或上傳冒充正式版的產物。
