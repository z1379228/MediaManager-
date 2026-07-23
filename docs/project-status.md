# 目前專案狀態

狀態日期：2026-07-23

## 結論

MediaManager 目前來源停在 Development `39.0.10`。既定 Development 34.0～39.0
工作已整併；使用者決定不建立 Development 40.0 或後續版本計畫。Repository
沒有可發布 Stable 候選。本輪僅授權 Development 39.0.10 的 stage、commit、
source freeze，以及建立本機、未簽署、`SAFE_MODE` 的 Testing 1.1；沒有簽署、
push 或發布授權。

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

## 已退役或取消

- 動畫瘋整合已自目前來源與 runtime 註冊移除；舊 UserData 與保留版本不改寫。
- 已取消的 Stable 1.0 候選、舊 Testing 候選與未授權 build 工作目錄都不是
  可發布資產。
- Development 40.0 與後續 roadmap 為 `NO PLAN / NO RELEASE`，不以空版本續號。

## 目前 Testing 工作

- Testing 公開身分為 `1.1.0`，預定本機路徑為 `Version/Testing/1.1`。
- Testing 1.0 是不可覆寫的歷史版本，不以目前 39.x 來源重建或冒用。
- 本輪產物必須是未簽署 `SAFE_MODE`；是否已建立及其雜湊，以版本資料夾內的
  `release-info.json` 與 `SHA256SUMS.txt` 為準。
- Authenticode、production Ed25519、GitHub tag／release、push 與發布均不在授權內。

## 尚未成立的發行條件

- 沒有同一候選集上的 production Authenticode、Ed25519、checksum、SBOM、
  copied-folder smoke 與 release preflight 證據。
- 截圖只能證明可見版面；Tab／Shift+Tab、UIA／NVDA、讀屏、Windows 高對比及
  真實互動流程仍需人工驗證。
- 外部網站會變動；離線 regression 與 extractor 存在不等於即時網站 smoke。

這些未成立項目不阻擋本機 Testing 1.1，但阻擋任何 Stable 或公開發布宣稱。

## 歷史與回復

目前樹不保留逐版 roadmap 與重複 release journal。過去決策仍可從 Git 歷史、
不可變 `Version/` 產物及 GitHub Releases 的 checksum／metadata 追查。不得為了
縮小 Repository 而刪除公開附件、改寫 tag、重寫 Git 歷史或清除 UserData。
