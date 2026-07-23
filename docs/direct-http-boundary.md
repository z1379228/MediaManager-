# Direct HTTP MOD 能力邊界

`direct-http` 是全新 profile 預設啟用、具有獨立工作區的直接檔案父 MOD；既有保存狀態保持不變。它不是通用網站解析器，
也不作為其他網站 MOD 失敗時的後備方案。

## 接受範圍

- 只接受 HTTPS、無帳密、無自訂連接埠、無 fragment，且路徑以明確允許副檔名結尾。
- 初始主機與每次重新導向都要解析為全域公開 IP；私有、回送、link-local、保留與
  無法解析的位址全部拒絕。
- YouTube、Bilibili、動畫瘋、Facebook、Instagram、Threads（`threads.com`／舊
  `threads.net`）、X/Twitter、MEGA（`mega.io`／`mega.nz`）
  及既有通用影音站網域全部排除，必須回到各自 MOD。
- 單檔上限 64 GiB；一次最多建立 100 個工作。

## 下載與完整性

- 下載先寫入同一輸出資料夾的隱藏 `.part`；只有伺服器回應 206 時才附加續傳，否則
  重新寫入部分檔。
- 成功後原子更名；既有目的檔不覆寫。
- 單檔可選填預期 SHA-256。雜湊不符會刪除該部分檔，不把內容標記為完成。
- 暫停或程式中止時可保留部分檔供下次明確繼續；乾淨啟動不會自動開始網路工作。

## 明確排除

不處理 HTML 頁、HLS/DASH manifest、登入、Cookie、DRM、付費、地區、廣告、短網址
解析、檔案分享站 API 或未知副檔名。需要網站語意的內容必須另建具最小權限的網站
父 MOD 與子 MOD。
