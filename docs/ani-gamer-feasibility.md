# 動畫瘋整合（已退役）

狀態：`HISTORICAL / REMOVED IN 38.1.15 / NO RELEASE`

本文件只保留為 Development 38.1.0～38.1.14 的歷史索引。依使用者的範圍決定，
38.1.15 已從目前來源移除動畫瘋父 MOD、目錄搜尋、集數導覽、相容性播放器與離線索引入口；
G38-02 已標記 `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`。

- 歷史 Development 38.0 產物與 38.1.x 驗證紀錄不覆寫。
- 既有 UserData、歷史紀錄、離線索引與使用者自行選取的本機檔案不刪除、不遷移。
- 舊設定中的 `ani-gamer*` ID 只視為已退役的未知項目，不能使啟動失敗，也不能重新註冊功能。
- 不得把動畫瘋網址重新接到通用 Direct HTTP、yt-dlp、ffmpeg 或其他下載 adapter。
- [Direct HTTP 邊界](direct-http-boundary.md) 繼續拒絕已知網站頁面、登入內容、串流 manifest、
  DRM、廣告、Cloudflare、Cookie／profile 與其他存取限制繞過。

目前執行狀態與後續順序以
[Development 34.0～40.0 唯一版本更新計畫](roadmap-development-34.0-40.0.md) 為準。
