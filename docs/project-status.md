# 目前專案狀態

狀態日期：2026-07-27

## 結論

MediaManager 目前工作來源為 Development `39.0.12`，新增以單一 YouTube
搜尋結果建立公開相似音樂候選的入口。已封存的 Testing `1.2.0` 仍以
Development `39.0.11` 為來源，不包含相似音樂入口；它保留為本機歷史候選且
未發布。Development `39.0.12` 已被選為 Testing `1.2.1` 候選來源，source
freeze、未簽署 EXE、自包含 ZIP、tag `test-v1.2.1`、GitHub Release 與上傳均
已獲授權，但在本機及遠端驗證完成前仍是 `AUTHORIZED / PENDING / NOT
PUBLISHED`。Development 40.0 仍為 `NO PLAN / NO RELEASE`，Repository 也沒有
可發布 Stable 候選。目前已存在的未簽署、`SAFE_MODE` Testing 1.1 仍是
`test-v1.1.0-r2`。其 GitHub metadata 目前誤設
為非 prerelease 並被視為 Latest，待另行授權修正；這不等於 Stable 發行。

## 已完成範圍

- 核心、可信 UI、下載佇列、媒體庫、版本與 MOD 生命週期已有非 UI 回歸。
- YouTube、Bilibili、MEGA、Direct HTTP 與 generic Beta 的網站權限分離。
- 官方媒體主機採 exact-host、窄路徑與 provider/site-matrix 一致性檢查。
- 外部 MOD 提供 schema v2、Ed25519 發布者信任、依賴圖、交易復原、受控程序
  與宣告式 UI。
- 格式工廠、localhost-only Gopeed Bridge、選用 Speech to Text 與 Automation
  已納入內建 MOD 管理。
- 可信桌面使用 channel-neutral `MediaManager v1.0` 產品名稱；實際核心與發布
  metadata 仍維持三軌分離。
- Development 39.0.12 的 YouTube 工作區可由單一選取結果啟動相似音樂搜尋；
  候選只使用公開搜尋與既有本機排序，不使用 Cookie、私人推薦或觀看紀錄。

## 已退役或取消

- 動畫瘋整合已自目前來源與 runtime 註冊移除；舊 UserData 與保留版本不改寫。
- 已取消的 Stable 1.0 候選、舊 Testing 候選與未授權 build 工作目錄都不是
  可發布資產。
- Development 40.0 與後續 roadmap 為 `NO PLAN / NO RELEASE`，不以空版本續號。

## 目前 Testing 工作

- Testing `1.2.0` 本機封存已存在於 `Version/Testing/1.2`，版本稽核確認核心
  為 Development `39.0.11`。封存來源固定為 revision
  `fab5cb9333274e54f65a35b2f44a86699f0f349f`；目前 39.0.12 工作樹不會回寫
  該不可變候選；GitHub 上沒有對應 Testing 1.2.0 Release 或 tag。
- Testing `1.2.1` 必須建立於 `Version/Testing/1.2.1`，由同一個乾淨的
  Development `39.0.12` source revision 執行 receipt-bound build、staging、
  runtime audit、copied-folder smoke 與 deterministic ZIP 比對。
- Testing `1.2.1` 的預定 tag 是 `test-v1.2.1`，主要下載附件是
  `MediaManager-Testing-1.2.1.zip` 與同名 `.zip.sha256`；目前不得提供假下載
  URL 或宣稱已發布。
- Testing 1.0 是不可覆寫的歷史版本，不以目前 39.x 來源重建或冒用。
- Testing 1.1 使用唯一修訂 tag `test-v1.1.0-r2`，精確指向 source revision
  `09b3a86e00938241d27050088583ebf81d9fb182`；9 個附件已發布且 digest 閉合。
- 產物維持未簽署 `SAFE_MODE`；實際身分與雜湊以發行頁的
  `release-info.json`、`SHA256SUMS.txt` 與 ZIP sidecar 為準。

## 尚未成立的發行條件

- 沒有同一候選集上的 production Authenticode、Ed25519、checksum、SBOM、
  copied-folder smoke 與 release preflight 證據。
- 截圖只能證明可見版面；Tab／Shift+Tab、UIA／NVDA、讀屏、Windows 高對比及
  真實互動流程仍需人工驗證。
- 外部網站會變動；離線 regression 與 extractor 存在不等於即時網站 smoke。

這些未成立項目不阻擋 Testing 使用，但阻擋任何 Stable 或已簽署正式發布宣稱。

## 歷史與回復

目前樹不保留逐版 roadmap 與重複 release journal。過去決策仍可從 Git 歷史、
不可變 `Version/` 產物及 GitHub Releases 的 checksum／metadata 追查。不得為了
縮小 Repository 而刪除公開附件、改寫 tag、重寫 Git 歷史或清除 UserData。
