# MediaManager 開發版 29.0 計畫

狀態：Development 打包中。28.0 的 P0／P1 已完成離線驗證，P2 已建立安全基線但仍未啟用。
29.0 以「可重現、可診斷、可維護」為主，不把未簽署的 Gopeed 或 P2P 引擎接入核心，
也不代表可以建立 Testing 或 Stable 產物。

目前進度：29.0.1～29.0.6 已完成離線實作與回歸；29.0.7 與封版驗證將在產物建立後執行，
仍不代表 Stable 或 Testing 發布。

## 29.0 目標

1. **發布候選可重現**：來源 revision、依賴、wheel、EXE、版本資訊與 SHA-256 必須能
   從同一份提交來源重建，copied-folder 啟動結果一致。
2. **日常工作流穩定**：下載佇列、批量操作、試聽／預覽、歷史替代與清理工作不會在
   重啟、停用 MOD 或部分失敗時靜默遺失或自動重跑。
3. **MOD 自檢可用**：以唯讀檢查呈現父／子狀態、四語言、路由、完整性、依賴與按鈕
   可用性；自檢不連網、不啟動 provider、不修改使用者資料。
4. **維護成本下降**：網站能力矩陣、依賴快照、錯誤分類與測試 fixture 變成單一可
   追蹤來源，避免各工作區重複判定。

核心仍不放入網站專屬解析器。未啟用父 MOD 時不建立子 MOD 工作區；指定網站失敗
時必須 fail closed，不改由 YouTube 或 generic provider 猜測處理。

## 28.0 → 29.0 開發區塊

| 版本 | 專注區塊 | 預定交付 | 放行條件 |
| --- | --- | --- | --- |
| 29.0.1 | 發布重現基線 | 鎖定 source fingerprint、依賴快照、建置輸出、`release-info.json` 與 `SHA256SUMS.txt`；保留 current／previous 回退；CI 加入版本稽核 | Ruff、pytest、版本／MOD／污染稽核與 copied-folder smoke 均可由同一提交重跑 |
| 29.0.2 | 下載佇列與批量控制 | 全選／取消、批次取消、清除已完成、逐項重試、預覽停止、暫停與重啟後保持暫停 | 無乾淨啟動自動下載；取消清理 `.part`；狀態與歷史可恢復 |
| 29.0.3 | MOD Self Check | 唯讀檢查 registry、父子啟用、四語言、路由、manifest／hash、依賴、控制項與選用傳輸安全基線 | 不連網、不啟動外部程序；每個失敗都有可定位原因與修復提示 |
| 29.0.4 | 網站契約與診斷 | YouTube／Bilibili／動畫瘋／MEGA／Facebook／Generic 的錯誤分類與 site-matrix fixture 統一 | 零筆、403、缺依賴、部分失敗、取消與不支援網域不混用 |
| 29.0.5 | UI 維護性 | 拆分大型控制器、統一刷新節流、縮圖快取上限、鍵盤／可存取名稱與 940×620 回歸 | 不改變既有父子 MOD 路由；無白屏、破圖或背景工作殘留 |
| 29.0.6 | 外部工具診斷 | MEGAcmd、whisper-cli、語音模型與 yt-dlp EJS 的狀態、路徑、版本與修復說明統一 | 選用工具缺失不阻擋核心；不自動下載模型或執行未知安裝程式 |
| 29.0.7 | 第三方 MOD 開發基線 | 更新 schema v2、宣告式 UI、capability、runtime contract、簽章與 fixture 範例 | 空目錄可重現建立／驗證／停用流程；外部 UI 不可注入任意 Qt／HTML／腳本 |
| 29.0 | 開發版封版 | 整合已放行區塊，建立新的 `Version/Development/29.0/` 與集中更新紀錄 | 完整品質、依賴、provider smoke、簽署演練、copied-folder 與上傳前後雜湊全部記錄 |

## 優先級

### P0：發布與資料安全阻擋項

- 可重現建置、版本通道、current／previous 稽核與回退。
- 下載佇列不自動恢復、不靜默覆寫；暫停、取消、重試、清除與完成通知狀態一致。
- YouTube／Bilibili／動畫瘋的父子 MOD、錯誤分類、搜尋／批量工作流回歸。
- MOD Self Check 的唯讀結果、四語言覆蓋、manifest／SHA-256 與依賴狀態。

### P1：主要可用性與維護優化

- 批量工作區的選取／取消／清理、縮圖與試聽／預覽資源上限。
- site-matrix、provider failure taxonomy、依賴快照與 UI 狀態共用契約。
- UI 控制器拆分與刷新節流；所有長工作可取消且不在乾淨啟動執行。
- 第三方 MOD 作者可依文件完成最小父 MOD／子 MOD 的驗證與停用。

### P2：仍須獨立審查的候選

- Gopeed：只評估已安裝的本機實例；localhost、短期 token、預設關閉、明確使用者
  啟動與可撤銷授權。未取得獨立簽章與 runtime contract 前不註冊 provider。
- P2P／Torrent：只在獨立 MOD 內評估合法用途、儲存／頻寬配額、上傳／做種顯示；
  不加入內建 torrent 搜尋、自動開埠、代理繞過或核心引擎。
- 新網站：每個網域建立自己的父 MOD、子 MOD、manifest、路由、fixture 與 smoke；
  沒有證據不列為支援。

## 明確不納入 29.0

- DRM、登入、Cookie 匯入、付費／地區限制繞過、廣告跳過或 Cloudflare 繞過。
- 第五種語言、遙測、強制帳號、雲端同步、遠端控制、常駐剪貼簿監控。
- 未經使用者確認的自動替代影片、自動下載、自動恢復或自動開啟外部程序。
- 把 Gopeed、P2P／Torrent、瀏覽器擴充或新的通用解析器放入核心。

## 驗收矩陣

每個 29.0 區塊至少需要：

- 目標單元／契約測試與失敗案例；
- 四語言、父子 MOD、940×620、鍵盤與可存取名稱回歸；
- 依賴缺失、路由錯誤、部分來源失敗、取消與重啟案例；
- 文字污染、MOD 群組、site-matrix、版本與 SHA-256 稽核；
- 大版本封版才執行完整歷史稽核，日常只稽核 current＋previous。

## 發布規則

- 每個修正版使用新的 `Version/Development/29.0.x`，不得覆寫 28.0。
- 29.0.x 的內容集中寫入 `release-28.0-29.0.md`，不建立零散 release 文件。
- 開發版先保留完整證據與簡介；Testing／Stable 需另行評估，未取得使用者明確決定前
  不建立、不簽署、不上傳 Stable。
- P2 安全基線完成不等於 P2 runtime 功能可用；任何接入都需重新通過 manifest、簽章、
  capability、provider smoke 與 copied-folder 驗證。

## 29.0 封版狀態（2026-07-16）

Development 29.0 已建立於 `Version/Development/29.0/`。離線品質與完整性稽核已完成；
copied-folder EXE smoke 的 frozen windowed 收尾問題尚待修正版處理。未提供 production
簽章前不建立 Stable／Testing。
