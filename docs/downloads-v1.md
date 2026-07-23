# 下載工作契約 v1

核心只擁有優先佇列、持久歷史、取消、重試、進度快照、目的地與原子輸出。
網站 URL 辨識、metadata、播放清單及格式解析屬於各自下載 MOD。

## 佇列與恢復

- 佇列原子保存於 `Data/download-queue.json`。
- 關閉時為 `QUEUED`、`RUNNING` 或 `RETRYING` 的工作，下次啟動一律恢復為
  `PAUSED`；乾淨啟動不自動開始網路工作。
- 完成、失敗與取消工作留在歷史。恢復、重試與移除都需要使用者明確操作。
- 下載先寫入受限部分檔，驗證成功後原子更名；既有完成檔不靜默覆寫。
- 停用 MOD 會阻止新分析與新工作，並取消該 MOD 擁有的活動工作。

## 格式、容器與片段

YouTube 與 Bilibili 可依分析結果提供解析度、音訊 preset、字幕與 MP4／MKV／
WebM 容器選項。明確選擇與來源 codec 不相容時拒絕排隊並提出建議，不靜默
轉碼或改副檔名。

時間片段以秒保存，成為重複判定、檔名、重試與歷史的一部分。需要重編碼或
合併時由有界 FFmpeg 程序完成；失敗不得刪除已驗證可用的來源或 sidecar。

批次 TXT／CSV、播放清單與自動切割都先在可信 UI 預覽；只有使用者選取且整批
驗證通過後才原子加入佇列。任何單筆非法輸入不會被截斷成另一個 URL。

## 網站責任

- `youtube` 與 `bilibili` 是獨立 provider，擁有各自 host、capability 與矩陣。
- `mega` 只透過官方 `mega-get` 處理公開分享，見 [MEGA 邊界](mega-boundary.md)。
- `direct-http` 只處理明確檔案 URL，見 [Direct HTTP 邊界](direct-http-boundary.md)。
- `generic-ytdlp` 是預設停用的 Beta，相容範圍只以自身 site matrix 為準；
  不接管已具專用 MOD 的網站。
- 社群平台依 [官方工具邊界](social-platform-boundaries.md) 分離；不因 generic
  extractor 存在自動取得下載能力。
- 已退役的動畫瘋 ID 不會重新註冊，也不會轉送到 generic 或 Direct HTTP。

## 外部工具與程序

下載 MOD 只可經受控 provider host 執行核准工具。程序必須可取消、有 timeout、
有界 stdout／stderr、終止程序樹並回傳穩定錯誤分類。核心不把 shell、任意檔案、
瀏覽器 profile 或 Cookie DB 交給 provider。

完整依賴狀態見 [執行環境健康檢查](dependency-health.md)，精確主機與路徑見
[網站主機清冊](site-host-inventory.md)。

## 明確排除

MediaManager 不攔截播放串流、不從瀏覽器快取重建影片、不事後辨識並移除網站
廣告片段，也不繞過 DRM、登入、Cookie、Cloudflare、付費、地區或網站限制。
使用者只可保存自己有權保存的內容。
