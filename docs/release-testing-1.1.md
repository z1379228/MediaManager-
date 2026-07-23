# MediaManager Testing 1.1

- 通道：Testing
- Testing 身分：`1.1.0`
- 來源：Development `39.0.10` 的乾淨 source-freeze revision
- Source revision：`09b3a86e00938241d27050088583ebf81d9fb182`
- 本機路徑：`Version/Testing/1.1`
- 安全狀態：未簽署、`SAFE_MODE`
- 發布狀態：已於 2026-07-23 發布為 GitHub prerelease；不是 Latest 或 Stable
- Tag：`test-v1.1.0-r2`
- Release：[MediaManager 測試版 1.1（39.0.10 重整）](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.1.0-r2)

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
- Staged runtime audit 通過：Deno `2.9.2`、FFmpeg `8.1.2`，共 6 項檢查。
- `SHA256SUMS.txt` 的 105 個受控檔案全部閉合；GitHub 9 個附件的 digest 與
  本機逐檔 SHA-256 一致。
- Portable ZIP SHA-256：
  `31a1ab2c61ada07bc07eb8121107e8bbc7a16692347cae54af5fc5edb7dcf912`。
- Authenticode 狀態為 `NotSigned`，且沒有 production signed release manifest；
  這不阻擋 Testing prerelease，但仍阻擋 Stable Gate。
