# MediaManager 測試版 1.1

- 通道：Testing
- 測試版本：1.1.0
- 本機路徑：`Version/Testing/1.1`
- GitHub 標籤：`test-v1.1.0`
- 安全狀態：`SAFE_MODE`

## 本次測試重點

- 動畫瘋離線封存可匯入一部使用者本機影片與多個字幕側檔。
- 影片存放於 `media/`，字幕存放於 `subtitles/`，並由 `episode.json` 記錄相對路徑、大小、來源名稱與 SHA-256。
- 離線驗證會逐檔檢查影片與字幕，支援取消、大小上限、符號連結阻擋與原子寫入。
- 動畫瘋、MEGA、YouTube 及其他既有 MOD 維持父／子 MOD 分流與可停用設計。

## 測試限制

本測試版仍是未簽署的 `SAFE_MODE` 成品，不是 Stable 正式版。未整合 Cookie、登入、DRM、付費、地區或廣告繞過，也不會在乾淨啟動時自動下載或啟動外部工具。

建議測試回報：

<https://forms.gle/iUMyEDojsASoFyY16>
