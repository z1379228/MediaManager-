# MediaManager Testing 1.1

- 通道：Testing
- Testing 身分：`1.1.0`
- 來源：Development `39.0.10` 的乾淨 source-freeze revision
- 本機路徑：`Version/Testing/1.1`
- 安全狀態：未簽署、`SAFE_MODE`
- 發布狀態：僅授權本機打包；不 push、不簽署、不發布

## 測試範圍

- 核心下載佇列、媒體庫、可信 UI 與內建／第三方 MOD 生命週期。
- YouTube、Bilibili、MEGA、Direct HTTP 與網站矩陣明列的官方頁面工作區。
- 本機格式工廠、localhost-only Gopeed Bridge／P2P Transfer。
- 選用 Speech to Text 與 Automation；缺少選用工具不影響核心啟動。
- schema v2 外部 MOD、Ed25519 發布者信任、最小權限與宣告式 UI。

## 安全與相容限制

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站存取限制。
- 未簽署 Testing 產物不得改名或升格為 Stable，也不得取代歷史 Testing 1.0。
- 網站離線 regression 不等於即時網站可用；外部 runtime 與人工 UI 流程須個別
  記錄實測結果。
- UserData、版本附件與第三方 MOD 更新仍遵守原子寫入、備份與 fail-closed Gate。

## 驗證基線

- 完整 repository runner：`1317 passed, 7 skipped`。
- Quality audit、版本文件、MOD 群組、網站矩陣、依賴鎖與保留版本稽核通過。
- 打包後仍須驗證 staged runtime、checksum、release metadata、copied-folder
  smoke 及精確 `SAFE_MODE` 證據；結果以產物內 metadata 為準。
