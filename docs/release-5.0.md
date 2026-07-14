# MediaManager 5.0 Preview

狀態：工程功能完成，正式發布阻擋。來源版本為 `5.0.0`，build channel 固定顯示
`preview`；沒有 production Ed25519 與有效 Authenticode 前不得改成 stable。

## 封版驗證紀錄（2026-07-15）

- Ruff 全專案檢查通過。
- Pytest：`518 passed, 2 skipped`；兩項略過皆為目前 Windows 帳號無法建立符號連結。
- 依賴鎖定稽核：8 個直接依賴皆為精確版本。
- `Version/5.0` 已產生 EXE、wheel、依賴清單、CycloneDX SBOM、發布資訊與 SHA-256 清單。
- 從複製出的獨立資料夾執行 `--version`、`--verify-only`、`--headless` 與 GUI 啟動均通過，測試程序與副本皆已清理。
- 本機版本僅保留 current + previous：`5.0` 與 `4.5`；兩版各 43 項雜湊驗證通過。
- 正式發布預檢仍為 `BLOCKED`：編譯版尚未配置有效 production Ed25519 公鑰，且 Windows EXE 為 `NotSigned`。

## 搜尋

- UI 使用有界聯合搜尋，可選來源並顯示正常、錯誤、停用與部分失敗狀態。
- 每筆結果顯示縮圖、標題、作者、時長、媒體類型、來源與本機排序理由。
- Search v2 capability 由 MOD manifest 宣告，provider ID 或欄位錯誤時 fail-closed。
- 支援 cursor 分頁合約；分頁時必須指定單一來源。`youtube-search` 目前宣告
  `pagination=none`，UI 明示不支援，不製造假下一頁。
- 本機有界別名／拼字修正與穩定文字排序不送往第三方分析服務。

## 下載

- YouTube、Bilibili、generic-ytdlp 分析回傳有界實際格式、解析度、容器、編碼、
  音軌語言、字幕語言與容量估計。
- 分析後格式下拉只保留來源實際可達的畫質／音訊 preset；格式細節可在提示中
  檢查，未知容量保持未知。
- 單檔命名預覽、批量／播放清單選擇、優先級、磁碟與容量確認、重複偵測、
  個別失敗重試、暫停／取消、`.part` 續傳及重啟復原均已接入。
- 指定輸出已存在時拒絕覆蓋；播放清單與批量上限由 Download v2 capability
  實際控制。
- 長篇 BGM 的章節／音訊斷點草案、試聽確認與安全分段命名維持獨立 MOD。

## MOD 與網站

- 提供 Search／Download Adapter SDK、離線範例、契約驗證、依賴宣告與 JSON
  相容報告；驗證不執行第三方程式。
- YouTube、Bilibili、generic 站點矩陣分離；離線 contract audit 與公開內容
  live smoke 不混用。
- Facebook、Instagram、Threads 與動畫瘋維持官方入口；MEGA 只保留官方
  SDK／MEGAcmd 候選，不宣稱已支援下載。

## 發行與安全

- MIT LICENSE、8 項精確依賴鎖、dependency inventory、CycloneDX SBOM 與
  staged checksum 已整合。
- 日誌移除常見權杖、MEGA key 與 Windows 使用者名稱；無廣告、無遙測、無
  強制帳號。
- release preflight 同時要求正式 Ed25519 manifest 與 Authenticode。
- 目前外部簽署身分不存在，因此預期結果是 `SAFE_MODE Preview / BLOCKED for
  production`，不是 stable。

## 5.0 後候選

固定四語言 MOD UI 區塊、公開圖片集、逐字稿全文搜尋、跨站鏡像來源群組、
aria2 類直接傳輸、BitTorrent／Magnet、雲端同步與遠端管理全部留到 5.0 stable
之後重新評估，不是 Preview 或 stable 的放行阻擋條件。
