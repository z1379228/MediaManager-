# MediaManager 開發版 6.0

狀態：開發版大版本。此版本供新功能驗證與使用者回饋，不是正式版 1.0，且不
因功能完成而自動產生 Stable 封裝。

## 搜尋

- YouTube 搜尋最多顯示 50 筆，支援 200 筆有界結果視窗內的 offset 下一頁。
- 搜尋結果可依來源、內容類型、長度及四種介面語言訊號在本機篩選。
- 聯合搜尋保留來源隔離、去重、可解釋排序與部分失敗；錯誤分類不暴露例外
  細節以外的本機敏感資料。
- 歷史、失效影片替代、歌手／語言二次搜尋及隨機相似內容維持獨立 MOD，候選
  上限提高到 50，不建立背景推薦服務。

## MOD 適配

- 宣告式外部 MOD UI schema v2 僅接受英文、日文、簡體中文及繁體中文。
- MOD 未提供目前語言時回退到 manifest 內的預設語言；未知語言、主動內容與
  未通過安裝檔案驗證的 UI 仍 fail-closed。
- Search／Download Adapter SDK、權限、外部工具及核心相容範圍繼續離線驗證，
  驗證過程不安裝也不執行第三方程式。

## 下載

- 加入工作前以預估容量加上 256 MiB 安全保留檢查磁碟空間。
- 既有批次優先級、暫停／恢復、程式重啟復原、個別重跑、原子輸出與完成通知
  繼續由完整回歸測試保護。
- Bilibili 彈幕與長影片／BGM 切割維持網站／功能 MOD 邊界；切割草案必須由
  使用者試聽與確認。

## 雙軌版本與正式版控制

- 新開發大版本輸出到 `Version/Development/6.0`。
- Stable 建置未帶明確確認旗標時，建置與 staging 入口都會立即拒絕。
- `tools.release_candidate` 只產生候選評估。即使所有門檻通過，也只顯示建議
  正式版號並等待使用者決定。
- 既有 `Version/4.5`、`Version/5.0` 不搬動、不改寫，避免破壞歷史雜湊。

## 驗證

- Ruff：通過。
- Pytest：`531 passed, 2 skipped`；略過項目均為目前 Windows 帳號無法建立
  符號連結。
- `Version/Development/6.0` 已建立 EXE、`6.0.0` wheel、依賴清單、CycloneDX
  SBOM、發布資訊與 SHA-256 清單，共 43 項 staged checksum。
- 從完整複製資料夾執行 `--version`、`--verify-only`、`--headless` 與 GUI 啟動
  全部通過；測試程序與副本已清理。
- 清理前逐次揭露的 `3.9`、`4.0`、`4.5` 舊封裝均通過稽核後才移除；依
  current + previous 政策，完整歷史模式確認本機只保留且通過 `5.0` 與
  `Development/6.0`。
- 8 項直接依賴鎖定及 6 個網站／11 項網站能力矩陣全部通過。
- 正式版候選目前仍受 production Ed25519 與 Windows Authenticode 阻擋；
  Authenticode 實測為 `NotSigned`，開發版不會因此偽裝為 Stable。
