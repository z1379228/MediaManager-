# MediaManager 5.0 目標與放行門檻

5.0 完成後的雙軌發布規則及 5.1 至開發版 6.0 排程，統一記錄於
[`roadmap-development-6.0.md`](roadmap-development-6.0.md)。

狀態：5.0.0 Preview 工程驗收中，production stable 仍受正式簽署門檻阻擋。版本排序、4.x 分工與功能刪減以
`roadmap-4.0-to-5.0.md` 為唯一權威；本文件只定義什麼情況可以發布 5.0。

## 搜尋門檻

- UI 實際使用有界聯合搜尋，而不是只呼叫單一 `youtube-search` 舊路徑。
- 搜尋能力由 MOD 的版本化宣告提供，不再由核心替所有 provider 硬編碼 YouTube。
- 使用者可選來源並看見健康狀態、部分失敗、分頁與結果來源。
- 結果顯示縮圖、標題、作者、時長、媒體類型及排序／替代理由。
- 標題、歌手、時長、語言與類別排序只在本機執行；別名與拼字容錯有界，
  搜尋紀錄不送往第三方分析服務。
- YouTube 搜尋、歷史、相似、替代、播放器與自動切割維持可個別停用的 MOD，
  不重做完整 `music.youtube.com` 或常駐推薦系統。

## MOD 適配門檻

- 提供 Search/Download Adapter SDK、最小範例 MOD、合約測試器與相容性報告。
- MOD 可宣告網站、速率限制、必要工具、格式、字幕、彈幕、播放清單、分段、
  續傳及批次上限；核心對所有宣告執行 fail-closed 驗證。
- MOD 個別具有逾時、取消、熔斷、資源配額、錯誤分類與版本遷移；失敗不造成
  核心 UI 凍結、全白頁或其他 MOD 中斷。
- 4.x v2 合約保留相容期。若需要 v3，只能新增版本化合約與轉接層，不可原地
  改變第三方 MOD 已依賴的 v2 語意。
- YouTube、Bilibili 先完成離線與公開內容 smoke matrix；Facebook、Instagram、
  Threads 在獨立驗證前維持官方頁面入口，不得由 generic provider 宣稱支援。
- `mega` 保持獨立候選 MOD；下載只能走官方 MEGA SDK 或 MEGAcmd，不接收帳密、
  工作階段或規避傳輸配額。

## 下載門檻

- 分析後只顯示實際可用畫質、編碼、容器、音軌、字幕、彈幕與預估容量。
- 執行階段真正落實 `supports_playlist`、`max_batch_size`、`supports_resume`，
  不只停留在 schema 或警告文字。
- 有界重試決策接入佇列；永久失效、登入限制及內容移除不自動重試，使用者
  隨時可以停止。
- 批量／播放清單支援選集、多檔優先級、命名預覽、重複偵測與個別失敗重跑。
- 可續傳工作、磁碟空間預留、原子提交、程式重啟復原與完成／失敗通知通過測試。
- 長篇 BGM 先以章節與音訊斷點產生草案，使用者試聽確認後才切割輸出。

## 品質與正式發行門檻

- Ruff、完整 Pytest、版本一致性、built-in MOD 雜湊、current + previous 稽核、
  copied-folder GUI／headless smoke 與 4.x 升級／回退全部通過。
- `core/version.py`、`pyproject.toml`、README、wheel、`release-info.json`、
  `Version/5.0`、Git tag 與 GitHub Release 完全一致。
- 補齊專案 `LICENSE`、鎖定建置依賴，並把 dependency inventory／SBOM 納入
  staged checksum 與 GitHub 附件。
- 正式 `5.0.0` 必須同時具備正式 Ed25519 release manifest 與 Authenticode；
  缺少任一信任身分只能發布為 `SAFE_MODE Preview`，不得標示 stable。
- 診斷資料預設移除 URL 權杖、MEGA link key、Cookie、帳密、工作階段與使用者
  路徑；無廣告、無遙測、低背景資源占用維持不變。

## 5.0 不包含

- MOD 多語言 manifest／UI 區塊；此功能保留到 5.0 穩定後，且永久只支援
  `en`、`ja`、`zh-CN`、`zh-TW` 四種介面語言。
- 內建 BitTorrent、Magnet、ed2k、做種、torrent 搜尋或自動開啟連接埠。
- 雲端帳號同步、備份、上傳、WebDAV、遠端管理或跨裝置控制。
- 任意下載前後腳本、內建瀏覽器規避限制、私人／付費／DRM／地區限制處理。
- 同時加入大量未驗證網站，或把參考軟體直接變成安裝相依套件。
- 公開圖片集、逐字稿全文搜尋、跨站鏡像來源群組及 aria2 類直接傳輸整合。

上述 P2 能力只能在 5.0 穩定後，以預設停用的獨立 MOD 重新評估。
