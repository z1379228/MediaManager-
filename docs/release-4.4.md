# MediaManager 4.4 網站適配

狀態：來源里程碑完成。次版本只提供中文更新說明，不重建或覆寫 `v4.0.0`
大型附件。

## 已完成

- YouTube 新增獨立 `site-matrix.json`，與 Bilibili、generic-ytdlp 一起納入
  built-in 完整性與 release inventory。
- YouTube 離線矩陣涵蓋公開影片分析、有界格式摘要、播放清單選擇、分段下載、
  字幕與本機 FFmpeg 試聽。
- YouTube 政策邊界明確禁止 Cookie／自動登入、地區、DRM、付費、會員、廣告與
  私人內容限制繞過。
- Bilibili 矩陣持續覆蓋公開分析、多 P／番劇公開集數、字幕與 XML／ASS／MKV
  彈幕工作流。
- 離線 `site_quality_audit` 與需網路的 public-content live smoke 明確分離；
  live 報告標示 `mode=live-public-content`，不得用離線 PASS 冒充網站即時可用。
- MEGA 只保留獨立候選與官方連結驗證；未安裝、未啟用，也不宣稱下載支援。
  未來若實作只能使用官方 MEGA SDK 或使用者自行安裝的 MEGAcmd，不接收帳密、
  工作階段或規避傳輸配額。

## 驗證

- 離線網站品質稽核：6 個 generic 站點族群、11 個 YouTube／Bilibili 功能，PASS。
- 網站矩陣、smoke 報告與 release inventory 專項測試通過。
