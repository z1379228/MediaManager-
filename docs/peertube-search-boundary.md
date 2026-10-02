# PeerTube 公開實例搜尋邊界

## 目標

`peertube-search` 是預設啟用、按需啟動的內建搜尋 MOD。它讓使用者指定一個
PeerTube 公開實例，再以該實例的官方 REST API 搜尋該站本機影片。這項能力不在
乾淨啟動時建立程序或網路連線，也不把搜尋詞送到其他 PeerTube 實例或搜尋索引。

官方契約來源：

- [REST API 快速開始](https://docs.joinpeertube.org/api/rest-getting-started)
- [REST API 參考](https://docs.joinpeertube.org/api-rest-reference.html)
- [PeerTube OpenAPI](https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/api/openapi.yaml)

## 使用流程

1. 在「網站搜尋」選取 PeerTube。
2. 輸入文字關鍵字與完整的 HTTPS 實例根網址，例如 `https://video.example`。
3. MediaManager 呼叫 `/api/v1/search/videos`，固定送出 `searchTarget=local` 與
   `isLocal=true`，並將每頁數量限制在 1 至 50 筆、總視窗限制在 200 筆。
4. 回應只保留該實例本機、公開、已發布且非 NSFW 的影片。使用者可明確選擇
   在系統瀏覽器開啟結果。

PeerTube 是具實例範圍的來源，不參與「全部來源」聚合搜尋。變更實例網址會使
既有分頁游標失效，避免把不同實例的搜尋狀態混用。

## 網路與安全限制

- 實例只接受不含使用者資訊、非預設連接埠、路徑、查詢或 fragment 的 HTTPS
  根網址；文字搜尋欄拒絕網址。
- 連線前解析 DNS；只要任一結果不是全域公開 IP，整次請求即拒絕。連線固定到
  已檢查的 IP，同時保留原始主機名的 TLS 憑證驗證與 SNI，避免第二次 DNS 解析。
- 不跟隨 HTTP 重新導向，不傳送 Cookie、Authorization 或其他登入資料。
- 單次 timeout 為 20 秒，JSON 回應上限為 2 MiB；HTTP 429 及非成功狀態會明確
  回報，不以無限重試放大實例負載。
- 不讀取 API 回傳的縮圖網址，避免因顯示結果對使用者指定主機產生第二個隱含
  請求。搜尋只在使用者按下搜尋時啟動隔離 provider 程序。

## 非目標

本 MOD 不登入 PeerTube、不搜尋私密／未列出內容、不訂閱實例、不解析播放清單
或媒體串流，也不繞過存取限制。動態實例不會加入下載 provider 的靜態主機白名單，
所以結果只提供系統瀏覽器開啟，不會預填下載、排隊或下載檔案。

## 相容性、失敗與回復

Search v2 capability 新增可選的 `source_scope` 欄位。未宣告此欄位的既有 MOD
維持 `none`，行為不變；PeerTube 宣告 `https-origin`，因此核心要求單一來源與
明確實例。舊版游標不會被當成新版具實例範圍游標接受。

若 PeerTube 實例版本、政策或回應格式不相容，搜尋會失敗但不影響其他搜尋來源。
回復方式是停用 `peertube-search`；不需要資料遷移，也沒有需清理的訂閱、帳號或
下載狀態。
