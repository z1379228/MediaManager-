# 動畫瘋離線索引（已退役）

狀態：`HISTORICAL / REMOVED IN 38.1.15 / DATA RETAINED`

這是 Development 38.1.0～38.1.14 的歷史設計記錄，不再是目前產品能力。38.1.15
移除動畫瘋離線索引 UI 與 runtime 註冊，但不刪除、覆寫或遷移既有 UserData、封面、metadata、
驗證紀錄或使用者自行選取的本機媒體。

已退役資料不得自動匯入其他網站，也不得重新接到 Direct HTTP、通用 provider、瀏覽器 cache、
Cookie／profile、M3U8／金鑰／分段或串流擷取流程。若未來需要唯讀匯出或資料清理，必須另立
有明確資料範圍、備份、Rollback 與使用者授權的新工作。

目前執行狀態以
[Development 34.0～40.0 唯一版本更新計畫](roadmap-development-34.0-40.0.md) 為準。
