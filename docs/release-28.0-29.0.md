# 開發版 28.0～29.0 更新紀錄

本文件集中記錄 28.0 到 29.0 的開發內容。29.0 仍是 Development 軌，
不代表 Testing 或 Stable，也不建立正式版附件。

## 29.0.1 P0／發布基線

- CI 品質工作加入 `tools.audit_versions --root Version`，讓 Ruff、pytest、文字污染、
  MOD 群組、網站能力、依賴鎖與版本雜湊在同一個品質工作中檢查。
- Self Check 新增 `transport.boundary`，只讀確認 Gopeed／P2P 安全預設，禁止自檢連線、
  啟動程序、開啟埠或保存 token。
- 29.0 已切換 `core/version.py`，接下來建立新的 `Version/Development/29.0/`；
  不覆寫 28.0，也不建立 Stable 或 Testing 附件。

## 29.0.2 P0／下載佇列狀態與手動恢復

- `DownloadQueue` 的重啟回復規則維持 fail-closed：已保存的 `RUNNING`／`QUEUED` 工作只回復為 `PAUSED`，不會因啟動軟體而自動開始網路工作。
- `run_self_check()` 新增 `downloads.queue`，只讀取目前佇列快照，顯示各狀態數量；沒有附加佇列時只提出 warning，不啟動背景程序。
- 佇列、取消、暫停、恢復與持久化回歸測試，以及 29.0 品質工作流程測試均已加入。

## 29.0.3 P0／MOD Self Check 與安全傳輸邊界

- Self Check 現在涵蓋 MOD registry、父子啟用狀態、語言繫結、site matrix、provider smoke 匯入、傳輸邊界與下載佇列。
- Gopeed／P2P 僅驗證停用時的安全設定、localhost／路徑／容量／法律確認等邊界；未啟動外部程序、未連線、未註冊為可啟用 MOD。
- `tests/test_self_check.py`、`tests/test_transport_boundaries.py` 與 P0/P1 網站契約回歸測試通過；仍未宣稱第三方服務 live smoke 通過。

## 29.0.4 P0／網站錯誤契約與路由回歸

- YouTube（含 Music 子域）、Bilibili（含彈幕子 MOD）、動畫瘋、MEGA、Facebook 與 generic provider 的離線 site matrix、錯誤分類及父子路由回歸測試通過。
- 本階段只驗證契約、UI 路由與安全邊界；403、Cloudflare、登入限制與移除內容仍須由使用者在合法公開內容上另行執行 bounded smoke。

## 29.0.5 P1／佇列維護性與刷新資料來源

- `DownloadQueue.state_counts()` 提供包含所有狀態的穩定唯讀統計，Self Check 優先使用此契約；沒有新佇列 API 的測試替身仍可退回快照路徑。
- 佇列統計回歸涵蓋空狀態、取消後狀態與非法統計資料；未新增工作執行緒、網路連線或自動恢復行為。
- 這一階段先完成核心維護性，UI 仍依既有增量刷新與取消／暫停／恢復控制運作，避免重繪範圍擴大。

## 29.0.6 P0／MEGA 下載控制與錯誤分類

- MEGA 專用工作區的執行中工作現在會啟用暫停／取消；操作交由共用 `DownloadQueue` 終止受控 provider process，保留既有重啟後不自動恢復規則。
- 官方 `mega-get` 非零退出會保留最多 4,000 字元的有界輸出，讓配額、頻寬、服務中斷與連線重設可由共用錯誤分類器辨識；不把完整分享金鑰寫入錯誤文字。
- MEGA provider 完整性雜湊已同步更新；46 項 MEGA／provider failure／UI action state 回歸測試通過。

## 29.0 P0 待完成

- 從同一提交來源重建 wheel／EXE、copied-folder 啟動與 release evidence。
- 批量全選／取消、清理完成項、逐項重試與預覽／試聽停止的跨工作區回歸。
- YouTube、Bilibili、動畫瘋錯誤分類、父子狀態與自檢輸出整合。

## 29.0 P1／P2 邊界

- P1：UI 控制器拆分、刷新節流、縮圖上限、依賴診斷與第三方 MOD fixture。
- P2：Gopeed／P2P 只有 policy-only 安全基線；尚未註冊 runtime provider、未啟動外部
  引擎，也不提供 torrent 搜尋、自動開埠、遠端控制或核心傳輸。

## 驗證規則

- 每個 29.0.x 使用新的 `Version/Development/29.0.x`，不覆寫 28.0。
- 開發版日常只稽核 current＋previous；29.0 封版才執行完整歷史稽核。
- 沒有正式 Ed25519／Authenticode 身分與使用者明確決定前，不建立 Stable 或上傳正式版。

## 29.0 封版結果（2026-07-16）

- 已建立新的 `Version/Development/29.0/`，未覆寫任何既有版本，也未建立 Stable／Testing。
- 產物包含 `MediaManager.exe`、`mediamanager-29.0.0-py3-none-any.whl`、`release-info.json`、
  `SHA256SUMS.txt`、依賴／SBOM，以及通過雜湊驗證的 Deno／FFmpeg 便攜工具。
- Ruff 通過；pytest 為 882 passed、2 skipped；版本、MOD 群組、網站品質、依賴鎖定、文字污染與
  `git diff --check` 均通過。
- Development 成品維持 `SAFE_MODE`；正式 Ed25519／Authenticode preflight 仍阻擋，因此不宣稱 Stable。
- 複製資料夾的 EXE 命令列 smoke 在 frozen windowed executable 收尾階段未能正常返回，已停止該測試程序；
  這項問題保留為下一個修正版的包裝驗證項目，不影響 29.0 檔案完整性稽核。
