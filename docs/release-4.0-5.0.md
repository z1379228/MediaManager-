# MediaManager 開發版 4.0 至 5.0 更新紀錄

本文件以 4.0 合約基線為起點，集中記錄 4.x 到 5.0 的搜尋、下載、MOD 適配、
網站品質及發布工程變化。

## 4.0 基線

- `SearchCapabilityV2`、`DownloadCapabilityV2`、聯合搜尋後端及下載前能力驗證完成。
- 搜尋、批次、游標、縮圖及外部程序均有明確上限；開發版維持 `SAFE_MODE`。

## 4.1 搜尋清晰度

- UI 改用有界聯合搜尋，只查詢已啟用來源並顯示來源健康與部分失敗。
- 結果顯示縮圖、標題、作者、時長、媒體類型、來源及本機排序理由。
- 本機別名／拼字容錯不建立背景推薦或遙測。

## 4.2 下載準備

- YouTube、Bilibili 與 generic-ytdlp 回傳有界實際格式、容量及編碼摘要。
- 加入安全檔名預覽、批量／播放清單確認、磁碟空間與既有輸出拒絕覆蓋。
- `.part` 續傳、個別重試與恢復仍受 provider 能力與安全界線控制。

## 4.3 MOD 適配工具

- 新增 Search／Download Adapter SDK、最小離線範例及 JSON 相容報告。
- 驗證 schema、ID、入口、大小、symlink、權限、capability 與依賴宣告。
- 正式安裝仍須通過 schema v2、檔案清單、Ed25519、發布者信任及權限確認。

## 4.4 網站適配

- YouTube、Bilibili、generic-ytdlp 使用分離的網站品質矩陣。
- Bilibili 涵蓋公開多 P／番劇集數、字幕與 XML／ASS／MKV 彈幕路徑。
- MEGA、Facebook、Instagram、Threads 等未實測能力不宣稱可下載。

## 4.5 發布候選工程

- 加入 MIT LICENSE、8 項精確依賴鎖、dependency inventory 與 CycloneDX SBOM。
- 診斷資料移除敏感 query、MEGA link key 與 Windows 使用者路徑。
- copied-folder 啟動及 43 項 checksum 通過；因缺 production Ed25519 與
  Authenticode，僅能作為 `SAFE_MODE` 開發候選。

## 5.0

- 有界聯合搜尋、來源選擇、健康狀態、縮圖、分頁合約與可解釋排序完成整合。
- 下載格式、容量、命名、批次優先級、重複偵測、恢復與原子輸出進入同一工作區。
- Adapter SDK、網站品質矩陣、SBOM、依賴鎖及發布預檢完成。
- Ruff、518 項測試、copied-folder smoke 與 43 項 staged checksum 通過。
- production Ed25519 與 Authenticode 仍缺少，因此發布為開發版 Preview，不是正式版。

5.0 後的演進接續記錄於 [`release-5.0-6.0.md`](release-5.0-6.0.md)。
