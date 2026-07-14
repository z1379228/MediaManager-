# MediaManager 4.2 下載準備

狀態：來源里程碑完成。此版本不重建或覆寫 `v4.0.0` 大型附件，僅提供中文
更新說明；正式完整附件仍集中於 5.0。

## 已完成

- YouTube、Bilibili 與 generic-ytdlp 分析回傳最多 40 筆實際格式摘要；核心
  驗證格式 ID、容器、解析度、幀率、影音編碼與容量範圍。
- 下載頁顯示實際格式數、具容量資訊的格式數，以及目前命名預設的容量估計。
- 單一媒體會依標題、媒體 ID 與輸出格式產生安全檔名預覽，允許使用者修改。
- 一般批量、匯入與播放清單在入列前顯示項目數、格式、容量、磁碟可用量、
  輸出位置與檔名，再由使用者確認。
- 播放清單與批量上限改由 Download v2 capability 的 `supports_playlist` 與
  `max_batch_size` 實際控制，不再只停留在 schema。
- 指定輸出檔已存在時，preflight 直接拒絕，不覆蓋原檔。
- bundled yt-dlp MOD 明確啟用 `.part` 續傳並關閉覆蓋；佇列既有的個別重試、
  暫停、重啟復原與原子狀態保存維持不變。

## 邊界

- 容量是 extractor 提供的估計；來源未提供時明確顯示未知，不虛構數值。
- 安全 UI 仍使用有界命名 preset，不暴露任意 yt-dlp 參數或前後腳本。
- 不下載 DRM、付費、私人、登入或受限內容，也不處理網站限制規避。

## 驗證基線

- Ruff 通過。
- 完整 Pytest：509 passed、2 個 Windows symlink 能力測試明確 skipped。
- `Version/3.9` 與 `Version/4.0` inventory 稽核通過。
