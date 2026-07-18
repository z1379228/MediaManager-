# Development 33.0–34.0 更新紀錄

狀態：34.0 來源已完成 source freeze，尚未封裝。本文不是發行附件、Testing／Stable 宣告或
正式簽署證據；目前仍維持 `SAFE_MODE`。

## 33.0 基線

- 收斂下載佇列、通知、依賴快照、MOD 父子狀態與首次啟動選擇流程。
- 建立受控 pytest／品質稽核入口，避免從使用者目錄廣域收集測試或把舊暫存 ACL
  問題誤判為產品失敗。
- 保留既有 Development 歷史產物，不覆寫其 EXE、metadata 或 SHA-256。

## 34.0 來源更新

- 動畫瘋官方頁面的 `document-loaded` 與實際媒體播放狀態分離；Qt WebEngine 能力
  不足時只提供 exact-host 官方 HTTPS 系統瀏覽器 handoff，不讀取 Cookie、登入狀態、
  媒體 URL，也不繞過廣告、地區、付費或 DRM 限制。
- 本機播放器只有進入 `PlayingState` 才確認播放成功，並以穩定錯誤碼區分 runtime
  capability、來源與媒體錯誤；使用者本機檔案白名單與大小界線不變。
- 新增 staged portable runtime 的純離線政策稽核：要求六個工具／授權檔集合精確、
  Deno 與 FFmpeg 固定檔案雜湊符合政策、Deno license 可追溯至 Repository canonical
  source，且 `release-info.json.portable_tools` 與實際 staging 一致。
- 設定檔加入 schema 1 typed decode、64 KiB 上限、future／corrupt fail-closed、未知欄位
  保留與跨程序排他鎖；可信 UI 只在持久化成功後改變 runtime，避免 stale writer 覆寫
  不相關設定。升級安裝缺少首次 MOD 旗標時預設保留既有 MOD／工作狀態。
- 新增預設 dry-run 的 legacy／pre-schema1 設定回復工具（保留歷史 `pre-35` 檔名）；
  要求明確路徑、SHA-256、owned current
  backup、跨程序鎖與原子替換，不讀取或修改未指定的真實使用者設定。
- Feature／built-in MOD 交易在持久化或 runtime 失敗時補償狀態，並對已取消或無法
  證明可回復的工作明確記錄不可逆風險；子程序 provider 以單一有界 deadline 等待
  result 與 stderr，避免有效結果／晚到 stderr 的競爭。
- build 工具拒絕接管既有根目錄 `build/`、`mediamanager.egg-info` 或碰撞的 attempt
  目錄，只清理由本次執行可證明擁有的路徑；本輪沒有實際建立版本產物。
- 核心相容版本同步為 `34.0.0`，Development 顯示版本同步為 `34.0`；Testing 仍是
  獨立的 `1.1.0`，不可用數字大小跨發行軌比較或升格。

## 相容性

- Manifest schema、runtime protocol、既有第三方 provider 介面與歷史產物路徑不變；
  新增由 core self-check 驗證、供可信 UI 後續採用的加法式 provider capability v1 契約，
  沒有 API Breaking Change；本版不宣稱 capability-to-button routing 已完成。
  設定檔新增 schema 1；legacy 內容保留 exact-byte backup
  後原子升級，future schema 保持唯讀，並提供可驗證的 legacy／pre-schema1 回復流程。
- 第三方 MOD／adapter 若把 `maximum_core_version` 固定為 `32.1.0` 或 33.x，會依既有
  fail-closed 相容性規則拒絕在 34.0 載入。作者必須先完成相容性驗證，再發布包含
  34.0 的新版本範圍；本次不會靜默放寬上限。

## 發行與安全狀態

- 34.0 已依授權建立本機 source-freeze commits；尚未建立 EXE、wheel、SBOM、
  `release-info.json`、`SHA256SUMS.txt`、Testing／Stable、簽署或推送 Git。
- Production Ed25519、Authenticode、正式成品 runtime 稽核、copied-folder 啟動與完整
  provider／UI 人工矩陣仍是後續門檻；缺少任一項時不得宣稱正式發布就緒。
- 單一動畫瘋官方影片已有使用者自行完成官方年齡與廣告流程後的正片播放證據；此
  證據不保證其他影片、帳號、地區、時間或環境。

## Rollback

- source freeze 後的來源回退只對核准的 34.0 freeze commit 建立獨立 revert；freeze 前的
  工作樹不是可追蹤 revision，不宣稱 Git 歷史存在 32.1 source baseline。保留的
  `Version/Development/32.1` 只作既有產物與 UserData 相容性證據，不是來源回退點；
  不刪除 UserData、不修改 ACL、不覆寫該保留產物或任何已公開附件。
- 若 34.0 候選驗證失敗，保留失敗證據並停止在 Development；不得以移除 runtime、
  放寬簽章／hash 檢查或直接改名為 Testing／Stable 規避門檻。
- 設定格式回退只使用 [35→34 設定回復 Runbook](settings-pre35-rollback.md) 的明確
  dry-run／SHA／跨程序鎖／owned backup 流程；不得直接覆寫、刪除或猜測使用者設定。

## Validation

- 完整 Repository pytest：`1092 passed, 7 skipped`；略過項維持平台／symlink 能力條件。
- staged runtime policy 回歸：`19 passed, 1 skipped`；跳過項是 Windows 未提供目錄
  symlink 權限，另有不依賴 OS 權限的 fail-closed reparse 模擬回歸。
- 品質稽核：Ruff `355` 個 Python 檔與文字污染 `557` 個檔均通過；compileall 與
  `git diff --check` 通過。
- MOD group `8 groups / 4 locales`、網站 `13 sites / 42 features / 56 workflows`、
  依賴鎖定 `10`、版本文件 `34.0.0` 與保留版本 `5` 均通過。

尚未建立 staged 34.0 成品，因此 runtime policy CLI 仍只以隔離 fixture 驗證；上述
結果不宣稱正式 runtime 成品、EXE、Testing、Stable 或 production 簽章通過。
