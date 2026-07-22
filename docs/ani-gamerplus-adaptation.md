# aniGamerPlus 參考適配（已退役）

狀態：`HISTORICAL REFERENCE / REMOVED IN 38.1.15 / NO CODE IMPORT`

aniGamerPlus 的歷史唯讀差異掃描只曾用來比較通用命名、佇列、有限重試、日誌與本機完整性
概念；上游 GPL 程式碼未複製進 MediaManager。使用者已決定移除動畫瘋整合，因此這份文件
不再授權任何動畫瘋 provider、播放器、Cookie、串流或下載工作。

- 歷史 38.1.0～38.1.14 證據與不可變 Development 38.0 產物保留。
- 既有 UserData 與離線索引保留；不自動刪除或轉換。
- 不得將退役功能重新接到 generic Direct HTTP、yt-dlp、ffmpeg 或其他通用 adapter。
- Cookie／profile、Cloudflare／代理／地區規避、M3U8／key／segment、解密、廣告跳過／移除
  與播放串流攔截仍排除。

目前可借鑑的軟體模板與分級改由
[同類軟體與模板重掃](comparable-software-options.md) 維護。
